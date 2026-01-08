from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scraper import IdealitaScraper
import uvicorn
from typing import Optional

app = FastAPI(title="Idealista Scraper API")

class ScrapeRequest(BaseModel):
    ciudad: str
    tipo_propiedad: str = "venta"
    max_resultados: int = 10

@app.get("/")
async def root():
    return {"message": "API de Scraping para Idealista"}

@app.post("/scrape")
async def scrape_properties(request: ScrapeRequest):
    try:
        scraper = IdealitaScraper()
        propiedades = await scraper.scrape_idealista(
            ciudad=request.ciudad,
            tipo_propiedad=request.tipo_propiedad,
            max_resultados=request.max_resultados
        )
        return {
            "success": True,
            "total": len(propiedades),
            "propiedades": propiedades
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
