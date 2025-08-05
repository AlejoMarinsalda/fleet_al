# -*- coding: utf-8 -*-
{
    'name': 'Fleet MercadoLibre Cars',
    'version': '1.0.0',
    'author': 'Alejo Marinsalda',
    'category': 'Fleet',
    'depends': ['fleet'],
    'data': [
        'security/ir.model.access.csv',     # PRIMERO los permisos
        'data/meli_connector_data.xml',     # Luego el conector
        'data/cron.xml',                    # Finalmente el cron
    ],
    'description': 'Importa autos de MercadoLibre y cargarlos en flota',
    'installable': True,
    'auto_install': False,
}