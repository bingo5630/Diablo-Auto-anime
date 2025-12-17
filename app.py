if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render will assign the PORT
    app.run(host="0.0.0.0", port=port)
