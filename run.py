#!flask/bin/python
from app import app

#shut up about the secret key
app.secret_key = "CashTipv1.0.0"
app.run(use_reloader=True, threaded=True, host='0.0.0.0')
