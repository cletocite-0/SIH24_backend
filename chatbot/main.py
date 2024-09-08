from flask import Flask, request, jsonify

from models.route_query import obtain_question_router

app = Flask(__name__)


@app.route("/query", methods=["POST"])
def query():
    data = request.json
    question = data["question"]
    return jsonify(question_router.invoke({"question": question}))


if __name__ == "__main__":
    app.run()
