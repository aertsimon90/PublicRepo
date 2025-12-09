## 🌟 Public Code Repository Server

Share your code! **[https://publicrepo.pythonanywhere.com/](https://publicrepo.pythonanywhere.com/)**

Welcome to the **Public Code Repository Server**\! This project is a demonstration of how a simple **Flask API** can be used to allow anyone on the internet to upload files directly to a designated **GitHub repository** without needing a GitHub account or complex authentication.

This repository serves two main purposes:

1.  **A Shared Code Dump:** A public space where developers can easily share small code snippets and files from any programming language.
2.  **A Server Template:** It provides the `PublicRepoServer.py` code, allowing you to quickly set up your own open, file-uploading service backed by GitHub.

-----

## 🚀 How to Contribute a File

You can add any code snippet, configuration file, or text document to this repository instantly using our simple web interface.

### 🌐 Web Uploader (Live Demo)

To upload a file, please visit the live application:

**[https://publicrepo.pythonanywhere.com/](https://publicrepo.pythonanywhere.com/)**

1.  **File Path/Name:** Enter the desired file path (e.g., `my_script.js`, `python_snippets/hello.py`, or `README.md`).
2.  **File Content:** Paste your code or file content into the text box.
3.  **Commit Message (Optional):** Add a descriptive commit message.
4.  Click **"Upload File"**.

The file will be immediately added as a commit to this GitHub repository\!

-----

## 🛠️ Developer Setup: Create Your Own Public Repo Server

The core of this project is the **`PublicRepoServer.py`** file, which contains the **`GitHubAPI`** class and the Flask server logic. You can deploy this code yourself to manage file uploads for your own GitHub repository.

### 1\. Prerequisites

  * A **GitHub Repository** (it is recommended to use a new, public repository).
  * A **GitHub Personal Access Token (PAT)** with the `repo` scope (for pushing content).
  * **Python 3** and required libraries: `requests`, `Flask`, `base64`.
