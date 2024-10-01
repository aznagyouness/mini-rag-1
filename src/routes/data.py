from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse

import os

from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
import aiofiles
from models import ResponseSignal

from .schemes.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.db_schemas import DataChunk, Asset

from models.AssetModel import AssetModel
from models.enums.AssetTypeEnum import AssetTypeEnum

import logging
logger = logging.getLogger(__name__)

data_router = APIRouter(
    prefix='/api/v1/data',
    tags= ['api_v1', 'data']
)

#,app_settings : Settings = Depends(get_settings)
@data_router.post("/upload/{project_id}")

# data validation ==> validation json response ==> file path  
# ==> write in chunks (memory efficiency) ==> success json response

async def upload_data(request:Request, project_id : str, ff : UploadFile,
                      app_settings: Settings = Depends(get_settings)):
    
    project_model = await ProjectModel.create_instance(
        db_client = request.app.db_client
    )

    project = await project_model.get_project_or_create_one(project_id=project_id)


    #validate the file (file size & type):
    is_valid, result_signal = DataController().validate_uploaded_file(file=ff)
    
    if  not is_valid: 
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                     'signal' : result_signal
                    }
        )
    
    project_path_dir = ProjectController().get_project_path(project_id=project_id)

    file_path, file_id = DataController().generate_unique_filepath(
        orig_file_name=ff.filename,
        project_id=project_id
    )

    async with aiofiles.open(file_path, "wb") as f :
        while chunk := await ff.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
            await f.write(chunk)


    #store the assets into the database
    asset_model = await AssetModel.create_instance(
        db_client = request.app.db_client
    )

    asset_ressource =Asset(
        asset_project_id = project.id,        
        asset_name = file_id,
        asset_type = AssetTypeEnum.FILE.value,
        asset_size = os.path.getsize(file_path)
    )

    asset_record = await asset_model.create_asset(asset = asset_ressource)



    return JSONResponse(
            content = {
                     'signal' : ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                     'file_id' : str(asset_record.id)

                    }
        )


from pydantic import BaseModel
from typing import List, Any

# Define a Pydantic model excluding 'id' and 'type'
class Document_returned(BaseModel):
    page_content:str
    metadata: dict
    type: str

#creation of end point for processing :
#@data_router.post("/process/{project_id}", response_model=List[Document_returned])
@data_router.post("/process/{project_id}")

async def process_endpoint( request:Request, project_id : str, process_request : ProcessRequest):

    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    project_model = await ProjectModel.create_instance(
        db_client = request.app.db_client
    )

    project = await project_model.get_project_or_create_one(project_id= project_id)


    project_files_ids = []
    if process_request.file_id :
        project_files_ids = [process_request.file_id]

    else :
        asset_model = await AssetModel.create_instance(
            db_client = request.app.db_client
            )
        
        project_files = await asset_model.get_all_project_assets(
            asset_project_id = project.id,
            asset_type = AssetTypeEnum.FILE.value
        )

        project_files_ids = [
            record["asset_name"]
            for record in project_files
        ]

    if len(project_files_ids) == 0  :
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {
                "signal": ResponseSignal.NO_FILES_ERROR.value
            }
        ) 
    
    no_records = 0
    no_files =0

    # intantiate an object to be able to insert many chunks :
    chunk_model = await ChunkModel.create_instance(db_client= request.app.db_client)

    # we do this after pydantic verifying the existance & validation of chunks 
    if do_reset ==1 :
        await chunk_model.delete_chunks_by_chunk_project_id(
            chunk_project_id =project.id
        )

    process_controller = ProcessController(project_id)



    for file_id in project_files_ids:

        file_doc = process_controller.get_file_content(file_id=file_id)

        if file_doc is None :
            logger.error(f"Error while processing file : {file_id}, either file doesn't exist or file type is not supported")
            continue

        file_chunks = process_controller.process_file_content(
            file_content=file_doc, 
            file_id=file_id,
            chunk_size=chunk_size,
            overlap_size= overlap_size
            )
        
        if file_chunks is None or len(file_chunks)==0:
            return JSONResponse(
                status_code = status.HTTP_400_BAD_REQUEST,
                content = {
                    "signal": ResponseSignal.PROCESSING_FAILED.value
                }
            )

        file_chunks_record = [
            DataChunk(

                    chunk_text = chunk.page_content,
                    chunk_metadata = chunk.metadata,
                    chunk_order = i+1 , 
                    chunk_project_id  = project.id
            ) 
            for i, chunk in enumerate(file_chunks)
        ]

        # how many inserted chunks :
        no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_record)
        no_files +=1



    return JSONResponse(
            content = {
                "signal": ResponseSignal.PROCESSING_SUCESS.value,
                "inserted_chunks": no_records,
                "no_files": no_files
            }
        )

