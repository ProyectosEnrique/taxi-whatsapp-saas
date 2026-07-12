"""
Limiter compartido — evita fuerza bruta en login/registro y abuso de SMS
(forgot-password manda un SMS real por Twilio, con costo por envío).
Un solo módulo para que main.py y los routers lo importen sin ciclo.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
