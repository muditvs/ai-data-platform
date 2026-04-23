def process_data(file_path):
    # Placeholder for data processing logic
    # For example, read the file and do something
    try:
        with open(file_path, 'r') as f:
            data = f.read()
        # Simulate processing
        return {"processed": True, "length": len(data)}
    except Exception as e:
        return {"error": str(e)}