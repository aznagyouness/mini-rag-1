from fastapi import FastAPI, APIRouter, status, Request
from fastapi.responses import JSONResponse
from .schemes.nlp import PushRequest, SearchRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from models import ResponseSignal


import logging

logger = logging.getLogger(__name__)

nlp_router = APIRouter(
    prefix='/api/v1/nlp',
    tags= ['api_v1', 'nlp']
)

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(project_id=project_id )

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )

    if not project :
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {
                "signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value
            }
        )

    nlp_controller = NLPController(vectordb_client= request.app.vectordb_client,
                                   generation_client = request.app.generation_client,
                                   embedding_client = request.app.embedding_client
    )

    has_records = True
    page_no = 1
    inserted_items_count = 0
    idx = 0

    while has_records :
        page_chunks = await chunk_model.get_project_chunks(project_id= project.id, 
                                                           page_no = page_no)
        
        if not page_chunks or len(page_chunks)==0 :
            has_records =False
            break

        chunks_ids = list(range(idx, idx+len(page_chunks)))
        idx += len(page_chunks)

        if len(page_chunks):
            page_no += 1

        is_inserted = nlp_controller.index_into_vector_db(project = project,
                                                           chunks = page_chunks, 
                                                           do_reset = push_request.do_reset,
                                                           chunks_ids=chunks_ids)
        
        if not is_inserted :
            return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {
                "signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value
            }
        ) 

        inserted_items_count += len(page_chunks)

        return JSONResponse(
            content = {
                "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
                "inserted_items_count" : inserted_items_count,
                "is_inserted": is_inserted
            }
        ) 



@nlp_router.get("/index/info/{project_id}")
async def index_project_info(request: Request, project_id: str):

    project_model =  ProjectModel(db_client=request.app.db_client)

    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(vectordb_client = request.app.vectordb_client , 
                                   generation_client = request.app.generation_client, 
                                   embedding_client = request.app.embedding_client )
    
    try :

        collection_info = nlp_controller.get_vector_db_collection_info(project=project)

    except ValueError as e :
        logger.error(f"the raised value error is : {e}")
        return JSONResponse(
                status_code = status.HTTP_400_BAD_REQUEST,
                content = {
                    "signal": ResponseSignal.VECTORDB_COLLECTION_NOT_EXIST.value
                }
        )         
    
    return JSONResponse(
            content = {
                "signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value,
                "my content":  collection_info,
            }
    ) 


@nlp_router.post("/index/search/{project_id}")
async def index_project_search(request: Request, project_id: str, search_request: SearchRequest ):

    project_model =  ProjectModel(db_client = request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    nlp_controller = NLPController( vectordb_client = request.app.vectordb_client, 
                                    generation_client = request.app.generation_client,
                                    embedding_client = request.app.embedding_client)
    
    results = nlp_controller.search_vector_db_collection(project=project,
                                                        text=search_request.text, 
                                                        limit=search_request.limit)
    

    if not results : 
        JSONResponse(
            status_code = status.status.HTTP_400_BAD_REQUEST,
            content = {
                "signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value,

            }
        )

    return JSONResponse(
            content = {
                "signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
                "content": [result.dict() for result in results],

            }
        )
