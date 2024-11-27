from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from stores.llm.LLMEnums import DocumentTypeEnum
from typing import List
import json

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, embedding_client):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client

    def create_collection_name(self, project_id:str):
        return f"collection_{project_id}".strip()
    
    def reset_vector_db_collection(self, project:Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)
    
    def get_vector_db_collection_info(self, project:Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = self.vectordb_client.get_collection_info(collection_name=collection_name)

        return json.loads(
            json.dumps(collection_info, default= lambda x : x.__dict__)
        )
    
    def index_into_vector_db(self, project: Project,  chunks: List[DataChunk],
                                 chunks_ids : List[int],
                                 do_reset: bool = False):
        
        # step1 : get collection name 
        collection_name = self.create_collection_name(project_id = project.project_id)

        # step2 : manage items      ==> getting texts , metadatas from chunks respecting the schemas DataChunk
        texts = [c.chunk_text for c in chunks]
        metadatas = [c.chunk_metadata for c in chunks]
        vectors = [
            self.embedding_client.embed_text(text=text,
                                              document_type= DocumentTypeEnum.DOCUMENT.value) 
            for text in texts
        ]

        # step3 : create collection if not exists
        _ = self.vectordb_client.create_collection( collection_name=collection_name,
                                                    embedding_size= self.embedding_client.embedding_size,
                                                    do_reset= do_reset)

        # step4 : insert into vector db 
        _ = self.vectordb_client.insert_many(collection_name=collection_name, 
                                             texts=texts, 
                                             vector=vectors,
                                             metadata=metadatas,
                                             record_ids=chunks_ids,
                                            )

        return True
    
    
    
    def search_vector_db_collection(self, project: Project, text: str, limit: int=10):

        #step 1 : get the collection name 

        collection_name = self.create_collection_name(project_id = project.project_id )     
        
      
        #step 2 : converte into embedding vector 

        embeded_text = self.embedding_client.embed_text( text = text,
                               document_type= DocumentTypeEnum.QUERY.value )
        
        if not embeded_text or len(embeded_text) == 0:
            return False


        #step 3: search the similarity and give me the result resecting the limit of search 
        results = self.vectordb_client.search_by_vector( collection_name=collection_name,
                                                        vector= embeded_text,
                                                        limit= limit)
        
        if not results :
            return False
            

        return results
   
