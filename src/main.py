from fastapi import FastAPI
from routes import base, data, nlp

from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings

from .stores.llm.LLMProviderFactory import LLMProviderFactory
from .stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory

app = FastAPI()



async def startup_span():
    settings = get_settings()
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]


    # llm factory :
    llm_provider_factory = LLMProviderFactory(config = settings)

    # vector db factory :
    vector_db_provider_factory = VectorDBProviderFactory(config = settings)

    # embedding client:
    app.embedding_client = llm_provider_factory.create( provider_name = settings.EMBEDDING_BACKEND )
    app.embedding_client.set_embedding_model( model_id = settings.EMBEDDING_MODEL_ID, 
                                             embedding_size = settings.EMBEDDING_MODEL_SIZE )
    
    
    # generation client: 
    app.generation_client = llm_provider_factory.create( provider_name = settings.GENERATION_BACKEND )
    app.generation_client.set_generation_model( model_id = settings.GENERATION_MODEL_ID )


    #vector DB client:
    app.vectordb_client = vector_db_provider_factory.create( provider = settings.VECTOR_DB_BACKEND )
    app.vectordb_client.connect()



async def shutdown_span():
    app.mongo_conn.close()

#app.router.lifespan.on_startup.append(startup_span)
#app.router.lifespan.on_shutdown.append(shutdown_span)

app.on_event("startup")(startup_span)
app.on_event("shutdown")(shutdown_span)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)



