try:
    from catcare import create_app
    print("Successfully imported create_app from catcare")
    app = create_app()
    print("Successfully created app")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Error creating app: {e}")