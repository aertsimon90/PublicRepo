import requests
import base64
import json
import os
import random
from getpass import getpass

class GitHubAPI:
    def __init__(self, username, repository, token):
        self.username = username
        self.repository = repository
        self.base_url = f"https://api.github.com/repos/{username}/{repository}/contents/"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _get_sha(self, targetfile):
        url = self.base_url + targetfile
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json().get('sha')
        return None

    
    def get_file(self, targetfile, local_path=None):
        url = self.base_url + targetfile
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('type') == 'file':
                content_base64 = data.get('content', '')
                content = base64.b64decode(content_base64)
                
                if local_path:
                    try:
                        
                        with open(local_path, 'wb') as f:
                            f.write(content)
                        return f"Success: File saved to {local_path}"
                    except Exception as e:
                        return f"Error: Failed to save file locally: {e}"
                
                
                return "".join([chr(h) for h in content])

            return f"Error: {targetfile} is not a file."
        elif response.status_code == 404:
            return f"Error: {targetfile} not found (404)."
        return f"Error: Failed to fetch file. Status Code: {response.status_code}"

    def set_file(self, targetfile, content, commit_message="File updated/created."):
        url = self.base_url + targetfile
        
        sha = self._get_sha(targetfile)

        if isinstance(content, str):
            content_base64 = base64.b64encode(bytes([ord(h) for h in content])).decode('utf-8')
        elif isinstance(content, bytes):
             content_base64 = base64.b64encode(content).decode('utf-8')
        else:
             return "Error: Content must be string or bytes.", None

        payload = {
            "message": commit_message,
            "content": content_base64
        }
        
        if sha:
            payload["sha"] = sha

        response = requests.put(url, headers=self.headers, data=json.dumps(payload))
        
        if response.status_code in [200, 201]:
            return "Success", response.json()
        return f"Error: Failed operation. Status Code: {response.status_code} - {response.json().get('message', 'Unknown Error')}", None

    def del_file(self, targetfile, commit_message="File deleted."):
        url = self.base_url + targetfile
        
        sha = self._get_sha(targetfile)
        
        if not sha:
            return f"Error: {targetfile} not found or SHA not retrieved.", None

        payload = {
            "message": commit_message,
            "sha": sha
        }

        response = requests.delete(url, headers=self.headers, data=json.dumps(payload))

        if response.status_code == 200:
            return "Success", response.json()
        return f"Error: Failed to delete file. Status Code: {response.status_code} - {response.json().get('message', 'Unknown Error')}", None

    def list_dir(self, targetdir=""):
        url = self.base_url + targetdir
        
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            contents = response.json()
            if isinstance(contents, list):
                return [{"name": item['name'], "type": item['type']} for item in contents]
            return f"Error: {targetdir} is not a directory."
        elif response.status_code == 404:
            return f"Error: Directory {targetdir} not found (404)."
        return f"Error: Directory listing failed. Status Code: {response.status_code}"

    def create_dir(self, targetdir):
        file_path = f"{targetdir.rstrip('/')}/.gitkeep"
        content = " " 
        commit_message = f"Directory created: {targetdir}"
        
        result, data = self.set_file(file_path, content, commit_message)
        
        if "Success" in result and data and data.get('content', {}).get('type') == 'file':
            return "Success", data
        return f"Error: Directory creation failed: {result}", data
            
    def del_dir(self, targetdir, commit_message="Directory deleted."):
        file_path = f"{targetdir.rstrip('/')}/.gitkeep"
        
        result, data = self.del_file(file_path, commit_message)
        
        if "Success" in result:
            return "Success", data
        elif "not found" in result:
             return f"Info: .gitkeep in {targetdir} not found. Directory might be empty.", data
        return f"Error: Directory deletion failed: {result}", data

    def is_file(self, targetpath):
        url = self.base_url + targetpath
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return 'dir'
            return data.get('type')
        return None

    
    def move_file(self, old_path, new_path, commit_message="File moved."):
        
        url_old = self.base_url + old_path
        response_old = requests.get(url_old, headers=self.headers)
        
        if response_old.status_code != 200:
            return f"Error: Failed to fetch old file content. Status Code: {response_old.status_code}", None
        
        data_old = response_old.json()
        if data_old.get('type') != 'file':
            return f"Error: {old_path} is not a file.", None
        
        content_base64 = data_old.get('content', '')
        content_bytes = base64.b64decode(content_base64)
        
        
        new_commit_message = f"Move: {old_path} -> {new_path}" if commit_message == "File moved." else commit_message
        status_set, data_set = self.set_file(new_path, content_bytes, new_commit_message)
        
        if "Success" not in status_set:
            return f"Error: Failed to create file at new path: {status_set}", data_set
            
        
        status_del, data_del = self.del_file(old_path, new_commit_message)
        
        if "Success" not in status_del:
        
            return f"Warning: File created at {new_path}, but failed to delete old file {old_path}. Delete manually. Error: {status_del}", data_set
        
        return f"Success: File moved from {old_path} to {new_path}", data_set

from flask import Flask, request

app = Flask(__name__)
gp = GitHubAPI("username", "repository", "GITHUB_PAT_TOKEN")

@app.route("/")
def main_path():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub File Uploader API</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        label {
            display: block;
            margin-top: 10px;
            font-weight: bold;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box; /* Ensures padding doesn't affect total width */
        }
        button {
            background-color: #2c974b;
            color: white;
            padding: 10px 15px;
            margin-top: 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }
        button:hover {
            background-color: #247c3c;
        }
        #status-message {
            margin-top: 20px;
            padding: 10px;
            border-radius: 4px;
            font-weight: bold;
            text-align: center;
            display: none; /* Hidden by default */
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>📤 Public GitHub Repository File Uploader</h1>
    <p>Use this form to add a new file to the **{{ username }}/{{ repository }}** repository.</p>
    <hr>
    
    <form id="uploadForm">
        <label for="file_name">File Path/Name (e.g., new_file.txt):</label>
        <input type="text" id="file_name" required>

        <label for="file_content">File Content (Plain Text):</label>
        <textarea id="file_content" rows="10" required></textarea>

        <label for="commit_message">Commit Message (Optional):</label>
        <input type="text" id="commit_message" placeholder="Default: File updated/created.">

        <button type="submit">Upload File</button>
    </form>
    
    <div id="status-message"></div>
</div>

<script>
    document.getElementById('uploadForm').addEventListener('submit', async function(event) {
        event.preventDefault(); // Prevent default form submission

        const fileName = document.getElementById('file_name').value;
        const fileContent = document.getElementById('file_content').value;
        const commitMessage = document.getElementById('commit_message').value || "File updated/created."; // Use default if empty
        const statusDiv = document.getElementById('status-message');

        statusDiv.style.display = 'block';
        statusDiv.className = '';
        statusDiv.textContent = 'Uploading... Please wait.';

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: fileName,
                    content: fileContent,
                    message: commitMessage
                })
            });

            const resultText = await response.text(); // Get response text

            if (response.ok) {
                // Status 200 (Successfuly)
                statusDiv.className = 'success';
                statusDiv.textContent = `✅ Success! File '${fileName}' uploaded. Server message: ${resultText}`;
                document.getElementById('file_name').value = '';
                document.getElementById('file_content').value = '';
                document.getElementById('commit_message').value = '';
            } else {
                // Status 400 or other errors
                statusDiv.className = 'error';
                statusDiv.textContent = `❌ Upload Failed. Status: ${response.status}. Server message: ${resultText}`;
            }
        } catch (error) {
            statusDiv.className = 'error';
            statusDiv.textContent = `❌ An unexpected error occurred: ${error.message}`;
            console.error('Fetch error:', error);
        }
    });
</script>

</body>
</html>"""

@app.route("/api/upload", methods=["POST"])
def api_upload():
    global gp
    data = request.get_json()
    name = str(data.get("name", ""))
    message = str(data.get("message", ""))
    content = str(data.get("content", ""))
    if name and content:
        if gp.is_file(name) == "file":
            return "File already exists.", 400
        gp.set_file(name, content, commit_message=message)
        return "Successfuly.", 200
    else:
        return "Name or content not found.", 400

if __name__ == "__main__":
    app.run(debug=True)
