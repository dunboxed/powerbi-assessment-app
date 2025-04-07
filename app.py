from flask import Flask, render_template, request, redirect, url_for, session, flash
import msal
import requests
import json
import os
from werkzeug.urls import url_quote_plus  # Explicitly import this



app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

template_dir = os.path.abspath(os.path.dirname(__file__))
app.template_folder = template_dir

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect():
    # Get credentials from form
    tenant_id = request.form.get('tenant_id')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    
    # Store in session
    session['tenant_id'] = tenant_id
    session['client_id'] = client_id
    session['client_secret'] = client_secret
    
    try:
        # Initialize MSAL app
        app_instance = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}"
        )
        
        # Get token
        result = app_instance.acquire_token_for_client(scopes=["https://analysis.windows.net/powerbi/api/.default"])
        
        if "access_token" not in result:
            flash(f"Authentication failed: {result.get('error_description')}", 'error')
            return redirect(url_for('index'))
        
        # Store token in session
        session['access_token'] = result["access_token"]
        
        # Get workspaces
        headers = {
            "Authorization": f"Bearer {result['access_token']}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://api.powerbi.com/v1.0/myorg/groups",
            headers=headers
        )
        
        if response.status_code != 200:
            flash(f"Failed to get workspaces: {response.text}", 'error')
            return redirect(url_for('index'))
        
        # Store workspaces in session
        workspaces = response.json()["value"]
        session['workspaces'] = workspaces
        
        return redirect(url_for('select_workspace'))
    except Exception as e:
        flash(f"Connection error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/select-workspace')
def select_workspace():
    if 'workspaces' not in session:
        flash("No workspace data available. Please connect first.", 'error')
        return redirect(url_for('index'))
    
    return render_template('select_workspace.html', workspaces=session['workspaces'])

@app.route('/select-report/<workspace_id>')
def select_report(workspace_id):
    try:
        # Get reports in this workspace
        headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports",
            headers=headers
        )
        
        if response.status_code != 200:
            flash(f"Failed to get reports: {response.text}", 'error')
            return redirect(url_for('select_workspace'))
        
        # Store workspace_id and reports in session
        reports = response.json()["value"]
        session['workspace_id'] = workspace_id
        session['reports'] = reports
        
        return render_template('select_report.html', reports=reports, workspace_id=workspace_id)
    except Exception as e:
        flash(f"Error loading reports: {str(e)}", 'error')
        return redirect(url_for('select_workspace'))

@app.route('/report-details/<report_id>')
def report_details(report_id):
    if 'reports' not in session:
        flash("Session expired. Please start over.", 'error')
        return redirect(url_for('index'))
    
    # Find report in session
    report = None
    for r in session['reports']:
        if r['id'] == report_id:
            report = r
            break
    
    if not report:
        flash("Report not found", 'error')
        return redirect(url_for('select_workspace'))
    
    # For demonstration, we'll just show basic report details
    # In a real implementation, this would run the design assessment
    
    return render_template('report_details.html', report=report)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
    
@app.errorhandler(500)
def handle_500(error):
    return "An unexpected error occurred", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
