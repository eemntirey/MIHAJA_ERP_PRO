from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    if debug:
        print('WARNING: Debug mode is enabled. Do not use in production.')
    
    app.run(debug=debug, host=host, port=port)
