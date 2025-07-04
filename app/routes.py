# app/routes.py - VERSÃO FINAL E CORRIGIDA

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import joinedload

# Importa o scraper e os schemas/modelos/funções necessários
from gsmarena_scraper import GSMArenaScraper
from . import schemas
from .database import db_session
from .models import Brand, Device, DeviceSpecification
from .utils import paginate_model

router = APIRouter()

# --- Função do Scraper para Rodar em Background ---
def run_scraper_task():
    """Esta função contém a lógica pesada que vai rodar em background."""
    print("Iniciando tarefa de scraping em background...")
    try:
        scraper = GSMArenaScraper()
        scraper.open_aws_gateway()
        scraper.parse_devices()
        scraper.close_aws_gateway()
        print("Tarefa de scraping em background concluída com sucesso.")
    except Exception as e:
        print(f"Erro durante a tarefa de scraping: {e}")

# --- Endpoint para Iniciar a Populacão do Banco de Dados ---
@router.get("/update_db", response_model=schemas.Response, include_in_schema=False)
async def update_db(background_tasks: BackgroundTasks):
    """
    Inicia a tarefa de scraping em background e retorna uma resposta imediata.
    O 'include_in_schema=False' esconde este endpoint da documentação pública da API.
    """
    background_tasks.add_task(run_scraper_task)
    return {"success": True, "message": "A atualização do banco de dados foi iniciada em segundo plano. Pode levar vários minutos."}

# --- O ENDPOINT DE BUSCA QUE VOCÊ QUER ---
@router.get("/search/{query}", response_model=list[schemas.DeviceNoBrandID])
async def search_devices_by_name(query: str):
    """
    Busca por aparelhos no banco de dados cujo nome contenha o texto da query.
    """
    # Prepara o termo de busca para ser case-insensitive
    search_query = f"%{query}%"
    
    # Faz a consulta no banco de dados
    devices = db_session.query(Device).filter(Device.name.ilike(search_query)).limit(25).all()

    # Se nada for encontrado, retorna um erro 404
    if not devices:
        raise HTTPException(status_code=404, detail="Nenhum aparelho encontrado com esse nome.")
    
    # Retorna a lista de aparelhos encontrados
    return devices

# --- Demais Endpoints (sem alterações) ---
@router.get("/devices/{device_id}", response_model=schemas.DeviceSpecDetail)
async def get_device_specificaitions(device_id: str):
    device = db_session.query(Device).options(joinedload(Device.specs), joinedload(Device.brand)).get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    grouped_specs = dict()
    for spec in device.specs:
        spec: DeviceSpecification
        category = spec.spec_category
        specification = spec.specification
        grouped_specs.setdefault(category, {})
        grouped_specs[category][specification] = spec.spec_value
        
    return dict(device=device, brand=device.brand, specifications=grouped_specs)

@router.get("/brands", response_model=schemas.BrandsResponse)
async def get_brands(page: int = 1, limit: int = 10):
    total_brands = db_session.query(Brand).count()
    brands = paginate_model(db_session, Brand, page, limit)
    return dict(total_brands=total_brands, brands=brands, page=page, size=limit)

