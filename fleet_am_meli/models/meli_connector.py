# -*- coding: utf-8 -*-
from odoo import api, fields, models
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class MeliConnector(models.Model):
    _name = 'meli.connector'
    _description = 'Conector para API de MercadoLibre'

    name = fields.Char(string='Nombre', required=True)
    access_token = fields.Char(string='Access Token', required=True)
    site_id = fields.Char(string='Site ID', default='MLA')
    active = fields.Boolean(string='Activo', default=True)

    @api.model
    def _get_default_headers(self):
        """
        Obtiene los headers por defecto para las peticiones
        """
        _logger.info("Obteniendo headers por defecto para MercadoLibre: %s %s", self.access_token,type(self.access_token))
        return {
            # 'Authorization': f'Bearer {self.access_token}',
            # 'Content-Type': 'application/json'
            'Authorization': 'Bearer APP_USR-8059881865312015-080419-c552702e6ecab04ffafbe1b6c1160f08-389541663',
            'Content-Type': 'application/json'
        }

    @api.model
    def _build_vehicles_payload(self, brand_ids=None, limit=400):
        """
        Construye el payload para búsqueda de vehículos
        """
        payload = {
            "domain_id": "MLA-CARS_AND_VANS",
            "site_id": self.site_id,
            "sort": {
                "attribute_id": "BRAND",
                "order": "asc"
            }
        }
        
        if brand_ids:
            payload["known_attributes"] = [
                {
                    "id": "BRAND",
                    "value_ids": brand_ids
                }
            ]
        
        if limit:
            payload["limit"] = limit
            
        return json.dumps(payload)

    @api.model
    def fetch_vehicles(self, brand_ids=None, limit=400):
        """
        Obtiene vehículos desde la API de MercadoLibre
        """
        url = "https://api.mercadolibre.com/catalog_compatibilities/products_search/chunks"
        
        payload = self._build_vehicles_payload(brand_ids, limit)
        headers = self._get_default_headers()

        try:
            response = requests.post(url, headers=headers, data=payload)
            _logger.info("Respuesta de MercadoLibre: %s %s", response.status_code,brand_ids)
            
            if response.status_code != 200:
                _logger.error("Error en API de MercadoLibre: %s", response.text)
                return {'success': False, 'error': response.text, 'data': []}
            
            data = response.json()
            vehicles = data.get('results', [])
            _logger.info("Vehículos obtenidos: %d", len(vehicles))
            
            return {'success': True, 'data': vehicles, 'total': len(vehicles)}
            
        except Exception as e:
            _logger.error("Error al conectar con MercadoLibre: %s", str(e))
            return {'success': False, 'error': str(e), 'data': []}

    @api.model
    def get_vehicle_details(self, vehicle_id):
        """
        Obtiene detalles específicos de un vehículo
        """
        url = f"https://api.mercadolibre.com/items/{vehicle_id}"
        headers = self._get_default_headers()

        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return {'success': False, 'error': response.text}
            
            return {'success': True, 'data': response.json()}
            
        except Exception as e:
            _logger.error("Error obteniendo detalles del vehículo %s: %s", vehicle_id, str(e))
            return {'success': False, 'error': str(e)}