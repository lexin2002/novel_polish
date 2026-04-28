
try:
    print('Importing app.api.rest...')
    from app.api.rest import router
    print('Rest imported')
    print('Importing app.api.ws...')
    from app.api.ws import websocket_logs
    print('WS imported')
except Exception as e:
    import traceback
    traceback.print_exc()
