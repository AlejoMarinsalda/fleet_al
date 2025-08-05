# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class FleetVehicleAl(models.Model):
    _inherit = 'fleet.vehicle'
    _description = 'Fleet Vehicle with MercadoLibre integration'

    meli_id = fields.Char(string='Meli ID', help='ID del vehículo en MercadoLibre')
    meli_url = fields.Char(string='URL MercadoLibre', help='URL del vehículo en MercadoLibre')
    meli_price = fields.Float(string='Precio MercadoLibre')
    
    # Nuevos campos para atributos de MercadoLibre
    vehicle_year = fields.Char(string='Año')
    trim = fields.Char(string='Versión')
    vehicle_type = fields.Char(string='Tipo de Vehículo')
    fuel_type = fields.Char(string='Tipo de Combustible')
    transmission = fields.Char(string='Transmisión')
    traction_control = fields.Char(string='Control de Tracción')
        
    @api.model
    def _get_meli_attributes_mapping(self):
        """
        Mapeo de atributos de MercadoLibre a campos del modelo
        Facilita el mantenimiento y extensión
        """
        return {
            'BRAND': {'field': 'brand_name', 'required': True, 'processor': '_process_brand'},
            'MODEL': {'field': 'model_name', 'required': True, 'processor': '_process_model'},
            'VEHICLE_YEAR': {'field': 'vehicle_year', 'required': False, 'processor': '_process_simple_value'},
            'VEHICLE_TYPE': {'field': 'vehicle_type', 'required': False, 'processor': '_process_simple_value'},
            'FUEL_TYPE': {'field': 'fuel_type', 'required': False, 'processor': '_process_simple_value'},
            'TRANSMISSION': {'field': 'transmission', 'required': False, 'processor': '_process_simple_value'},
        }

    @api.model
    def _extract_all_attributes(self, attributes):
        """
        Extrae todos los atributos relevantes de una vez
        Evita múltiples iteraciones sobre el mismo array
        """
        mapping = self._get_meli_attributes_mapping()
        extracted = {}
        
        # Inicializar con valores por defecto
        for meli_attr, config in mapping.items():
            field_name = config['field']
            extracted[field_name] = None
        
        # Extraer valores del array de attributes
        for attr in attributes:
            attr_id = attr.get('id')
            if attr_id in mapping:
                field_name = mapping[attr_id]['field']
                value = attr.get('value_name', '').strip()
                extracted[field_name] = value if value else None
        
        return extracted

    @api.model
    def _process_simple_value(self, value):
        """
        Procesa valores simples (texto)
        """
        if not value or value in ['Sin Valor', 'N/A', '']:
            return None
        return value.strip().title()

    @api.model
    def _process_brand(self, brand_name):
        """
        Procesa la marca (lógica existente)
        """
        if not brand_name or brand_name == 'Sin Marca':
            return None
            
        brand_name = brand_name.strip().title()
        
        brand = self.env['fleet.vehicle.model.brand'].search([
            ('name', 'ilike', brand_name)
        ], limit=1)
        
        if not brand:
            brand = self.env['fleet.vehicle.model.brand'].create({
                'name': brand_name
            })
            _logger.info("Nueva marca creada: %s", brand_name)
        
        return brand

    @api.model
    def _process_model(self, model_name, brand_id=None,fuel_type=None,transmission=None):
        """
        Procesa el modelo (lógica existente)
        """
        if not model_name or not brand_id:
            return None
            
        model_name = model_name.strip().title()
        
        model = self.env['fleet.vehicle.model'].search([
            ('name', 'ilike', model_name),
            ('brand_id', '=', brand_id)
        ], limit=1)
        
        if not model:
            model = self.env['fleet.vehicle.model'].create({
                'name': model_name,
                'brand_id': brand_id,
                'default_fuel_type': 'gasoline',  # Valor por defecto
                'transmission': 'automatic' if transmission == 'Automática' else 'manual',  # Valor por defecto
            })
            _logger.info("Nuevo modelo creado: %s", model_name)
        
        return model

    @api.model
    def _validate_required_attributes(self, attributes_data):
        """
        Valida que los atributos requeridos estén presentes
        """
        mapping = self._get_meli_attributes_mapping()
        errors = []
        
        for meli_attr, config in mapping.items():
            if config['required']:
                field_name = config['field']
                if not attributes_data.get(field_name):
                    errors.append(f"Atributo requerido faltante: {meli_attr}")
        
        return errors

    @api.model
    def _prepare_vehicle_values(self, vehicle_data, attributes_data, model_id):
        """
        Prepara los valores para crear el vehículo
        Separa la lógica de preparación de datos
        """
        values = {
            'name': vehicle_data.get('name', 'Vehículo sin título'),
            'meli_id': vehicle_data.get('id'),
            'model_id': model_id,
            # 'meli_url': vehicle_data.get('permalink'),
            # 'meli_price': vehicle_data.get('price', 0.0),
            # 'fuel_type': model_id.fuel_type,
            # 'transmission': model_id.transmission,
        }
        
        # Agregar atributos opcionales si tienen valor
        optional_fields = ['vehicle_year', 'trim', 'vehicle_type', 'fuel_type', 'transmission', 'traction_control']
        for field in optional_fields:
            if attributes_data.get(field):
                values[field] = attributes_data[field]
        
        return values

    @api.model
    def create_from_meli_data(self, vehicle_data):
        """
        Crea un vehículo desde datos de MercadoLibre
        Método principal optimizado
        """
        try:
            meli_id = vehicle_data.get('id')
            
            if not meli_id:
                return {'success': False, 'error': 'ID de MercadoLibre requerido'}
            
            # Verificar si ya existe
            existing = self.search([('meli_id', '=', meli_id)], limit=1)
            if existing:
                return {'success': False, 'error': f'Vehículo {meli_id} ya existe'}
            
            # Extraer todos los atributos de una vez
            attributes = vehicle_data.get('attributes', [])
            attributes_data = self._extract_all_attributes(attributes)
            
            # Validar atributos requeridos
            validation_errors = self._validate_required_attributes(attributes_data)
            if validation_errors:
                return {'success': False, 'error': '; '.join(validation_errors)}
            
            # Procesar marca
            brand = self._process_brand(attributes_data.get('brand_name'))
            if not brand:
                return {'success': False, 'error': 'No se pudo procesar la marca'}
            
            # Procesar modelo
            transmission = attributes_data.get('transmission', False)  # Valor por defecto
            fuel_type = attributes_data.get('fuel_type',False)  # Valor por defecto
            model_name = attributes_data.get('model_name')
            if not model_name:
                # Usar el nombre del vehículo como modelo si no hay MODEL específico
                model_name = vehicle_data.get('name', 'Modelo Genérico')
            
            model = self._process_model(model_name, brand.id,fuel_type,transmission)
            if not model:
                return {'success': False, 'error': 'No se pudo procesar el modelo'}
            
            # Preparar valores del vehículo
            vehicle_values = self._prepare_vehicle_values(vehicle_data, attributes_data, model.id)
            _logger.info("Valores de vehiculos obtenidos: %s", vehicle_values)
            
            # Crear vehículo
            vehicle = self.create(vehicle_values)
            
            _logger.info("Vehículo creado: %s con atributos: %s", 
                        meli_id, {k: v for k, v in attributes_data.items() if v})
            
            return {'success': True, 'vehicle': vehicle}
            
        except Exception as e:
            _logger.error("Error creando vehículo: %s", str(e))
            return {'success': False, 'error': str(e)}

    @api.model
    def importar_autos_masivo(self):
        """
        Método principal para el cron - Importación masiva desde MercadoLibre
        Este método conecta el conector con la creación de vehículos
        """
        _logger.info("=== INICIANDO IMPORTACIÓN MASIVA DE VEHÍCULOS ===")
        
        try:
            # 1. Buscar un conector activo (con sudo para evitar problemas de permisos)
            connector = self.env['meli.connector'].sudo().search([('active', '=', True)], limit=1)
            
            if not connector:
                _logger.error("No hay ningún conector de MercadoLibre activo")
                return {'success': False, 'error': 'No hay conector activo'}
            
            _logger.info("Usando conector: %s", connector.name)
            
            # 2. Definir marcas a importar (IDs de MercadoLibre)
            brand_ids = [
                "67695",    # Toyota
                "40661",    # Ford
                "60279",    # Chevrolet 
                "58955",    # Honda
                "389169",   # Nissan
                "60249",     # Volkswagen
                "40661"      # Audi
            ]
            
            # 3. Obtener vehículos desde la API
            _logger.info("Obteniendo vehículos de MercadoLibre...")
            api_response = connector.fetch_vehicles(brand_ids=brand_ids, limit=400)
            
            if not api_response['success']:
                _logger.error("Error en API de MercadoLibre: %s", api_response['error'])
                return {'success': False, 'error': api_response['error']}
            
            vehicles_data = api_response['data']
            total_vehicles = len(vehicles_data)
            _logger.info("Vehículos obtenidos de la API: %d", total_vehicles)
            
            if total_vehicles == 0:
                _logger.warning("No se obtuvieron vehículos de la API")
                return {'success': True, 'message': 'No hay vehículos para procesar'}
            
            # 4. Procesar cada vehículo
            created_count = 0
            updated_count = 0
            error_count = 0
            errors = []
            
            for i, vehicle_data in enumerate(vehicles_data, 1):
                _logger.info("Procesando vehículo %d/%d: %s", i, total_vehicles, vehicle_data.get('id'))
                
                try:
                    # Intentar crear el vehículo
                    result = self.create_from_meli_data(vehicle_data)
                    
                    if result['success']:
                        created_count += 1
                        _logger.info("✅ Vehículo creado: %s", vehicle_data.get('id'))
                    else:
                        # Si ya existe, es normal
                        if 'ya existe' in result['error']:
                            updated_count += 1
                            _logger.info("ℹ️ Vehículo ya existe: %s", vehicle_data.get('id'))
                        else:
                            error_count += 1
                            error_msg = f"ID {vehicle_data.get('id', 'unknown')}: {result['error']}"
                            errors.append(error_msg)
                            _logger.warning("⚠️ Error procesando vehículo: %s", error_msg)
                            
                except Exception as e:
                    error_count += 1
                    error_msg = f"ID {vehicle_data.get('id', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    _logger.error("❌ Excepción procesando vehículo: %s", error_msg)
            
            # 5. Resumen final
            _logger.info("=== IMPORTACIÓN COMPLETADA ===")
            _logger.info("Total procesados: %d", total_vehicles)
            _logger.info("Creados: %d", created_count)
            _logger.info("Ya existían: %d", updated_count)
            _logger.info("Errores: %d", error_count)
            
            if errors:
                _logger.warning("Errores encontrados: %s", "; ".join(errors[:5]))  # Solo primeros 5
            
            return {
                'success': True,
                'total_processed': total_vehicles,
                'created': created_count,
                'updated': updated_count,
                'errors': error_count,
                'error_details': errors
            }
            
        except Exception as e:
            _logger.error("Error crítico en importación masiva: %s", str(e))
            return {'success': False, 'error': f'Error crítico: {str(e)}'}

    # Métodos de compatibilidad (mantienen la interfaz existente)
    @api.model
    def _extract_brand_from_attributes(self, attributes):
        """Método de compatibilidad - usar _extract_all_attributes"""
        data = self._extract_all_attributes(attributes)
        return data.get('brand_name', 'Sin Marca')

    @api.model
    def _extract_model_from_attributes(self, attributes):
        """Método de compatibilidad - usar _extract_all_attributes"""
        data = self._extract_all_attributes(attributes)
        return data.get('model_name', 'Sin Modelo')