from flask import Flask, render_template, request, redirect, url_for, session, flash
import msal
import requests
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Log startup information
logger.info("Starting PowerBI Assessment App")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir('.')}")

# Handle template directory correctly
if os.path.exists('templates'):
    logger.info("Templates directory found")
    template_dir = os.path.join(os.getcwd(), 'templates')
else:
    logger.info("Templates directory not found, using current directory")
    template_dir = os.getcwd()

app.template_folder = template_dir
logger.info(f"Using template directory: {app.template_folder}")

@app.route('/')
def index():
    logger.info("Index route accessed")
    # Check if credentials are stored in environment variables
    tenant_id = os.environ.get('TENANT_ID')
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    
    # If all credentials exist, attempt auto-connect
    if tenant_id and client_id and client_secret:
        try:
            logger.info("Environment variables found, attempting auto-connect")
            # Store in session
            session['tenant_id'] = tenant_id
            session['client_id'] = client_id
            session['client_secret'] = client_secret
            
            # Initialize MSAL app
            app_instance = msal.ConfidentialClientApplication(
                client_id=client_id,
                client_credential=client_secret,
                authority=f"https://login.microsoftonline.com/{tenant_id}"
            )
            
            # Get token
            result = app_instance.acquire_token_for_client(scopes=["https://analysis.windows.net/powerbi/api/.default"])
            
            if "access_token" not in result:
                logger.error(f"Auto-authentication failed: {result.get('error_description')}")
                flash(f"Auto-authentication failed: {result.get('error_description')}", 'error')
                return render_template('index.html', environ=os.environ)
            
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
                error_details = response.json() if response.content else "No response content"
                logger.error(f"Failed to get workspaces: Status code {response.status_code}, Details: {error_details}")
                flash(f"Failed to get workspaces: {response.text}", 'error')
                return render_template('index.html', environ=os.environ)
            
            # Store workspaces in session
            workspaces = response.json()["value"]
            session['workspaces'] = workspaces
            
            return redirect(url_for('select_workspace'))
        except Exception as e:
            logger.error(f"Auto-connect error: {str(e)}")
            flash(f"Auto-connect failed: {str(e)}", 'error')
            return render_template('index.html', environ=os.environ)
    
    # If no environment variables, show the normal form
    return render_template('index.html', environ=os.environ)

@app.route('/connect', methods=['POST'])
def connect():
    logger.info("Connect route accessed")
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
            error_msg = f"Authentication failed: {result.get('error_description')}"
            logger.error(error_msg)
            flash(error_msg, 'error')
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
            error_details = response.json() if response.content else "No response content"
            logger.error(f"Failed to get workspaces: Status code {response.status_code}, Details: {error_details}")
            flash(f"Failed to get workspaces: {response.text}", 'error')
            return redirect(url_for('index'))
        
        # Store workspaces in session
        workspaces = response.json()["value"]
        session['workspaces'] = workspaces
        
        return redirect(url_for('select_workspace'))
    except Exception as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        flash(error_msg, 'error')
        return redirect(url_for('index'))

@app.route('/select-workspace')
def select_workspace():
    logger.info("Select workspace route accessed")
    if 'workspaces' not in session:
        flash("No workspace data available. Please connect first.", 'error')
        return redirect(url_for('index'))
    
    return render_template('select_workspace.html', workspaces=session['workspaces'])

@app.route('/select-report/<workspace_id>')
def select_report(workspace_id):
    logger.info(f"Select report route accessed for workspace: {workspace_id}")
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
            error_details = response.json() if response.content else "No response content"
            logger.error(f"Failed to get reports: Status code {response.status_code}, Details: {error_details}")
            flash(f"Failed to get reports: {response.text}", 'error')
            return redirect(url_for('select_workspace'))
        
        # Store workspace_id and reports in session
        reports = response.json()["value"]
        session['workspace_id'] = workspace_id
        session['reports'] = reports
        
        return render_template('select_report.html', reports=reports, workspace_id=workspace_id)
    except Exception as e:
        error_msg = f"Error loading reports: {str(e)}"
        logger.error(error_msg)
        flash(error_msg, 'error')
        return redirect(url_for('select_workspace'))

@app.route('/report-details/<report_id>')
def report_details(report_id):
    logger.info(f"Report details route accessed for report: {report_id}")
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
    logger.info("Logout route accessed")
    session.clear()
    return redirect(url_for('index'))

@app.route('/health')
def health():
    """Health check endpoint to verify the app is running"""
    logger.info("Health check endpoint accessed")
    return "OK", 200

@app.errorhandler(500)
def handle_500(error):
    logger.error(f"500 error: {str(error)}")
    return "An unexpected error occurred", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))  # Changed default port to 8000
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    logger.info(f"Starting Flask app on port {port} with debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)
