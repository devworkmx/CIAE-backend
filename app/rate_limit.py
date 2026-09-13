"""
Limitador de tasa (rate limiting) compartido por toda la aplicación.

Se usa especialmente en endpoints públicos (/api/public/*) para evitar
que un atacante pueda enumerar CURPs o folios haciendo peticiones masivas,
y en /api/auth/login para dificultar ataques de fuerza bruta.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
