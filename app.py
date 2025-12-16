from flask import Flask, request, jsonify, render_template
from mapping.mapping import generate_mapping
from services.autocomplete_service import autocomplete_service
from services.explain_service import explain_service

app = Flask(__name__)

EXCEL_PATH = "mapping/mapping.xlsx"
JSON_PATH = "mapping/mapping.json"

# Generate JSON from Excel at startup
generate_mapping(EXCEL_PATH, JSON_PATH)

@app.route("/")
def home():
    return render_template("main.html")

@app.route("/autocomplete", methods=["POST"])
def autocomplete():
    query = request.form.get("query", "").strip()
    search_mode = request.form.get("search_mode", "ipc").strip()

    if len(query) < 2:
        return jsonify({"suggestions": []})

    try:
        suggestions = autocomplete_service(query, search_mode, JSON_PATH)
        return jsonify({"suggestions": suggestions[:10]})
    except Exception as e:
        return jsonify({"suggestions": [], "error": str(e)})


@app.route("/explain_term", methods=["POST"])
def explain_term():
    query = request.form.get("query", "").strip()
    selected_title = request.form.get("selected_title", "").strip()
    search_mode = request.form.get("search_mode", "ipc").strip()

    if not query:
        return jsonify({"error": "Please enter a search term"}), 400

    try:
        result, status_code = explain_service(query, selected_title, search_mode, EXCEL_PATH, JSON_PATH)
        if "error" in result:
            return jsonify(result), status_code
        return jsonify(result),200
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

