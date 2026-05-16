---

# 🚀 GitExplorer

### Git-based AI Analytics and Summarization Agent

---

## 🌐 About the Project

**GitExplorer** is a web application that helps developers **explore, analyze, and understand Git repositories** in a simple and efficient way.

It acts as an **automated system** that collects repository data and presents it in a clear, structured format. This helps in tracking code changes, analyzing contributors, and generating useful insights.

The platform supports both **GitHub** and **Gitea**, making it flexible for different development environments.

---

## ✨ Features

* 🌐 **Multi-Platform Support**
  Connect to GitHub and Gitea repositories using access tokens.

* 📊 **Repository Analytics**
  View:

  * Total commits
  * Additions and deletions
  * Contributor activity
  * Overall code changes

* 🔍 **Search & Filters**
  Easily find commits using:

  * Author name
  * Commit message
  * Date range
  * Branch

* 📄 **Diff Viewer**
  Understand changes with clear, line-by-line file comparisons.

* 🌗 **Light & Dark Mode**
  Clean and user-friendly interface.

* ⚡ **Fast Performance**
  Optimized for handling large repositories smoothly.

* 📥 **Export Data**
  Download commit history as a CSV file.

* 🕒 **Session Memory**
  Quickly access recently viewed repositories.

---

## 🛠️ Tech Stack

### Frontend

* React (Vite)
* CSS (Custom Styling)
* Lucide Icons

### Backend

* FastAPI (Python)
* PyGithub
* HTTPX

---

## 🧩 How It Works

1. User enters repository details and access token
2. Backend fetches data from GitHub/Gitea APIs
3. Data is processed and structured
4. Frontend displays analytics, filters, and diffs
5. User can explore and export results

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/gitexplorer.git
cd gitexplorer
```

---

### 2. Backend Setup

```bash
cd backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8001
```

---

### 3. Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

---

### 4. Run the Application

Open your browser and go to:

```
http://localhost:5173
```

---

## 🔐 Usage Notes

* Use a **Personal Access Token**:

  * GitHub → `repo` permission
  * Gitea → `read:repository` permission

* The app shows **API rate limits** to help manage usage.

---

## 📌 Project Goal

The goal of GitExplorer is to build an **automated system for Git analytics and summarization** that helps developers:

* Understand repository activity
* Track changes efficiently
* Analyze contributors
* Generate structured insights

---

## 🤝 Contributing

Contributions are welcome!

If you’d like to improve this project:

* Fork the repository
* Create a new branch
* Submit a pull request

---

## 📄 License

This project is open-source and available under the MIT License.

---

## ❤️ Acknowledgement

Built with a focus on **automation, simplicity, and developer productivity**.

---

### ⚠️ Note

Replace:

```
your-username/gitexplorer
```

with your actual GitHub repository link.

---
