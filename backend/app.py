"""
AutoReport AI – Flask backend.

Exposes the five endpoints required by the frontend:

    POST /upload    — accept a CSV/Excel file, persist it, return a file_id
    POST /process   — run the six-agent pipeline on a previously uploaded file
    GET  /dashboard — return cached KPI + chart data for a file_id
    GET  /report    — return the generated PDF report URL for a file_id
    POST /chat      — forward a question to the chatbot agent

Each agent is a self-contained module under `agents/`. The orchestrator
in this file runs them in the exact order specified by the spec.
"""
from __future__ import annotations

import io
import os
import uuid
import traceback
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import Config
from database import db, Upload, Report, ProcessRun

# ---- Agent imports --------------------------------------------------------
from agents.data_cleaning_agent import DataCleaningAgent
from agents.analysis_agent import AnalysisAgent
from agents.kpi_agent import KpiAgent
from agents.dashboard_agent import DashboardAgent
from agents.report_agent import ReportAgent
from agents.chatbot_agent import ChatbotAgent


# ---- In-memory cache ------------------------------------------------------
# A simple per-file_id cache of the latest pipeline output so the dashboard
# endpoint can re-serve results without rerunning the whole pipeline.
RESULTS_CACHE: dict[str, dict] = {}


def create_app(config_class: type = Config) -> Flask:
    """Application factory."""
    # Resolve frontend build path relative to this backend folder
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_build = os.path.join(os.path.dirname(backend_dir), 'frontend', 'build')

    app = Flask(
        __name__,
        static_folder=frontend_build,
        static_url_path='/'
    )
    app.config.from_object(config_class)

    # CORS for the React dev server.
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Ensure folders exist.
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

    # Init DB.
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # ----- Helpers ---------------------------------------------------------
    def _allowed(filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in app.config['ALLOWED_EXTENSIONS']

    def _load_dataframe(stored_path: str) -> pd.DataFrame:
        """Read CSV/Excel into a DataFrame based on file extension."""
        ext = os.path.splitext(stored_path)[1].lower()
        if ext == '.csv':
            return pd.read_csv(stored_path)
        if ext in {'.xlsx', '.xls'}:
            return pd.read_excel(stored_path)
        raise ValueError(f"Unsupported file type: {ext}")

    # ----- Serve uploaded reports -----------------------------------------
    @app.route('/reports/<path:filename>', methods=['GET'])
    def serve_report(filename):
        return send_from_directory(
            app.config['REPORT_FOLDER'],
            filename,
            as_attachment=False,
        )

    # ----- Health ----------------------------------------------------------
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok', 'service': 'autoreport-ai'})

    # ----- POST /upload ---------------------------------------------------
    @app.route('/upload', methods=['POST'])
    def upload():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file part in the request.'}), 400

            file = request.files['file']
            if not file or file.filename == '':
                return jsonify({'error': 'No file selected.'}), 400

            if not _allowed(file.filename):
                return jsonify({
                    'error': 'Unsupported file. Please upload a .csv, .xlsx or .xls file.'
                }), 400

            # Persist file.
            original_name = secure_filename(file.filename)
            ext = os.path.splitext(original_name)[1].lower().lstrip('.')
            file_id = uuid.uuid4().hex
            stored_name = f"{file_id}_{original_name}"
            stored_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
            file.save(stored_path)
            size = os.path.getsize(stored_path)

            # Quick sanity check — must be a readable, non-empty dataset.
            try:
                df = _load_dataframe(stored_path)
            except Exception as e:
                os.remove(stored_path)
                return jsonify({
                    'error': f"Could not read the dataset: {e}"
                }), 400
            if df.empty or len(df.columns) == 0:
                os.remove(stored_path)
                return jsonify({
                    'error': 'The dataset is empty or has no columns.'
                }), 400

            upload_row = Upload(
                file_id=file_id,
                original_filename=original_name,
                stored_path=stored_path,
                file_type=ext,
                size_bytes=size,
            )
            db.session.add(upload_row)
            db.session.commit()

            return jsonify({
                'file_id': file_id,
                'filename': original_name,
                'rows': int(len(df)),
                'columns': int(len(df.columns)),
                'message': 'Upload successful.',
            }), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Upload failed: {e}'}), 500

    # ----- POST /process --------------------------------------------------
    @app.route('/process', methods=['POST'])
    def process():
        try:
            data = request.get_json(silent=True) or {}
            file_id = data.get('file_id') or request.args.get('file_id')
            if not file_id:
                return jsonify({'error': 'file_id is required.'}), 400

            upload_row = Upload.query.filter_by(file_id=file_id).first()
            if not upload_row:
                return jsonify({'error': 'Unknown file_id. Upload the dataset first.'}), 404

            run = ProcessRun(
                upload_id=upload_row.id,
                file_id=file_id,
                status='running',
            )
            db.session.add(run)
            db.session.commit()
            run_id = run.id

            # ⚠️ Extract plain Python values BEFORE the session closes.
            # Accessing ORM attributes inside the SSE generator (a different
            # execution context) causes 'not bound to a Session' errors.
            stored_path = upload_row.stored_path
            upload_id   = upload_row.id

        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Processing failed: {e}'}), 500

        import json

        def generate():
            """SSE generator — yields one event per agent step."""
            def sse(event: str, payload: dict) -> str:
                return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

            try:
                with app.app_context():
                    run_obj = db.session.get(ProcessRun, run_id)

                    # 1. Load & clean -------------------------------------------------
                    yield sse('progress', {'agent': 0, 'label': 'Data Cleaning Agent'})
                    df = _load_dataframe(stored_path)  # use plain str, not ORM obj
                    df_clean = DataCleaningAgent().run(df)
                    yield sse('progress', {'agent': 0, 'label': 'Data Cleaning Agent', 'done': True})

                    # 2. Analysis ----------------------------------------------------
                    yield sse('progress', {'agent': 1, 'label': 'Analysis Agent'})
                    analysis = AnalysisAgent().run(df_clean)
                    yield sse('progress', {'agent': 1, 'label': 'Analysis Agent', 'done': True})

                    # 3. KPIs --------------------------------------------------------
                    yield sse('progress', {'agent': 2, 'label': 'KPI Generation Agent'})
                    kpis = KpiAgent().run(df_clean)
                    yield sse('progress', {'agent': 2, 'label': 'KPI Generation Agent', 'done': True})

                    # 4. Dashboard (charts) -----------------------------------------
                    yield sse('progress', {'agent': 3, 'label': 'Dashboard Generation Agent'})
                    charts = DashboardAgent().run(df_clean)
                    yield sse('progress', {'agent': 3, 'label': 'Dashboard Generation Agent', 'done': True})

                    # 5. Report (PDF) ------------------------------------------------
                    yield sse('progress', {'agent': 4, 'label': 'Report Generation Agent'})
                    report_meta = ReportAgent(
                        report_folder=app.config['REPORT_FOLDER'],
                        file_id=file_id,
                    ).run(df_clean, analysis, kpis, charts)
                    yield sse('progress', {'agent': 4, 'label': 'Report Generation Agent', 'done': True})

                    # 6. Chatbot — initialise but don't ask a question here.
                    yield sse('progress', {'agent': 5, 'label': 'Chatbot Agent'})
                    forecast_chart = next((c for c in charts if 'forecast_meta' in c), None)
                    forecast_meta = forecast_chart['forecast_meta'] if forecast_chart else None

                    chatbot = ChatbotAgent(
                        api_key=app.config['OPENAI_API_KEY'],
                        model=app.config['OPENAI_MODEL'],
                    )
                    chatbot.prime(df_clean, forecast_meta)
                    yield sse('progress', {'agent': 5, 'label': 'Chatbot Agent', 'done': True})

                    # Track the report row.
                    report_row = Report(
                        upload_id=upload_id,  # plain int, not ORM obj
                        file_id=file_id,
                        filename=report_meta['filename'],
                        path=report_meta['path'],
                    )
                    db.session.add(report_row)

                    # Mark the run as successful.
                    run_obj.status = 'success'
                    run_obj.finished_at = datetime.utcnow()
                    db.session.commit()

                    # Keep the chatbot warm in memory so /chat is fast.
                    ChatbotAgent.cache_set(file_id, chatbot)

                    result = {
                        'status': 'success',
                        'kpis': kpis,
                        'charts': charts,
                        'analysis': _analysis_for_api(analysis),
                        'report_url': report_meta['url'],
                        'report_filename': report_meta['filename'],
                    }
                    RESULTS_CACHE[file_id] = result
                    yield sse('result', result)

            except Exception as agent_err:
                traceback.print_exc()
                with app.app_context():
                    run_obj = db.session.get(ProcessRun, run_id)
                    if run_obj:
                        run_obj.status = 'error'
                        run_obj.message = str(agent_err)
                        run_obj.finished_at = datetime.utcnow()
                        db.session.commit()
                yield sse('error', {'error': f'Processing failed: {agent_err}'})

        from flask import Response
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            },
        )

    # ----- GET /dashboard -------------------------------------------------
    @app.route('/dashboard', methods=['GET'])
    def dashboard():
        file_id = request.args.get('file_id')
        if not file_id:
            return jsonify({'error': 'file_id is required.'}), 400

        if file_id in RESULTS_CACHE:
            cached = RESULTS_CACHE[file_id]
            return jsonify({
                'kpis': cached.get('kpis'),
                'charts': cached.get('charts'),
            }), 200

        return jsonify({
            'error': 'No processed data for this file. Run /process first.'
        }), 404

    # ----- GET /report ----------------------------------------------------
    @app.route('/report', methods=['GET'])
    def report():
        file_id = request.args.get('file_id')
        if not file_id:
            return jsonify({'error': 'file_id is required.'}), 400

        report_row = (
            Report.query.filter_by(file_id=file_id)
            .order_by(Report.created_at.desc())
            .first()
        )
        if not report_row:
            return jsonify({'error': 'No report generated for this file.'}), 404

        return jsonify(report_row.to_dict()), 200

    # ----- POST /chat -----------------------------------------------------
    @app.route('/chat', methods=['POST'])
    def chat():
        try:
            data = request.get_json(silent=True) or {}
            file_id = data.get('file_id')
            question = (data.get('question') or '').strip()

            if not file_id or not question:
                return jsonify({'error': 'file_id and question are required.'}), 400

            if not app.config.get('OPENAI_API_KEY'):
                return jsonify({
                    'error': 'OPENAI_API_KEY is not configured on the server.'
                }), 503

            chatbot = ChatbotAgent.cache_get(file_id)
            if chatbot is None:
                # Lazily rebuild from the stored upload if we lost the cache
                # (e.g. after a server restart).
                upload_row = Upload.query.filter_by(file_id=file_id).first()
                if not upload_row:
                    return jsonify({'error': 'Unknown file_id.'}), 404

                df = _load_dataframe(upload_row.stored_path)
                df_clean = DataCleaningAgent().run(df)
                charts = DashboardAgent().run(df_clean)
                forecast_chart = next((c for c in charts if 'forecast_meta' in c), None)
                forecast_meta = forecast_chart['forecast_meta'] if forecast_chart else None

                chatbot = ChatbotAgent(
                    api_key=app.config['OPENAI_API_KEY'],
                    model=app.config['OPENAI_MODEL'],
                )
                chatbot.prime(df_clean, forecast_meta)
                ChatbotAgent.cache_set(file_id, chatbot)

            answer = chatbot.ask(question)
            return jsonify({'answer': answer}), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Chat failed: {e}'}), 500

    # ----- Catch-all SPA Routing ------------------------------------------
    # Serve index.html or static assets for any non-API routes.
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def index(path):
        # Prevent routing API calls to index.html (return a clean 404 instead)
        if path.startswith(('upload', 'process', 'dashboard', 'report', 'chat', 'health', 'reports')):
            abort(404)
        
        static_folder = app.static_folder
        if static_folder and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)
            
        if static_folder and os.path.exists(os.path.join(static_folder, 'index.html')):
            return send_from_directory(static_folder, 'index.html')
            
        return "Backend is running. Build frontend to view the UI."

    return app


def _analysis_for_api(analysis: dict) -> dict:
    """Trim heavy bits of the analysis payload before sending to the UI."""
    if not isinstance(analysis, dict):
        return {}
    out = dict(analysis)
    # Drop the raw correlation matrix from the API response (can be large),
    # but keep a count for the UI to display.
    if 'correlation' in out and isinstance(out['correlation'], dict):
        out['correlation'] = {
            'columns': list(out['correlation'].keys()),
            'note': 'See backend logs for full matrix.',
        }
    return out


# ---- WSGI / Vercel entrypoint ---------------------------------------------
# Expose a module-level `app` so that Vercel, gunicorn, and any other WSGI
# server can discover the Flask application without executing __main__.
#   gunicorn command : gunicorn app:app
#   Vercel           : detects `app` automatically in app.py
app = create_app()

if __name__ == '__main__':
    # Local development only.
    app.run(host='0.0.0.0', port=5000, debug=True)