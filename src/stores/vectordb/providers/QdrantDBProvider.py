from qdrant_client import models, QdrantClient
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums
import logging 
from typing import List

class QdrantDBProvider(VectorDBInterface):

    def __init__(self, db_path, distance_method: str):

        self.client = None
        self.db_path = db_path 
        self.distance_method = None

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = models.Distance.COSINE
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT           

        self.logger = logging.getLogger(__name__)

    
    def connect(self):
        self.client = QdrantClient(path = self.db_path)

    
    def disconnect(self):
        self.client = None

#======================================== essai =============================================================================
    def is_collection_existed(self, collection_name:str) -> bool:
        return self.client.collection_exists(collection_name=collection_name) 


    def list_all_collections(self) -> List:
        return self.client.get_collections()


    def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)


    def delete_collection(self, collection_name: str):
        if self.is_collection_existed(collection_name = collection_name):
            return self.client.delete_collection(collection_name = collection_name)
        

 
    def create_collection(self, collection_name:str,
                                embedding_size: int,
                                do_reset: bool = False):
        #delete a collection 
        if do_reset :
            _ = self.delete_collection(collection_name = collection_name)
        
        #check the existance before creating
        if not self.is_collection_existed(collection_name = collection_name):
            _ = self.client.create_collection(
                                            collection_name=collection_name,
                                            vectors_config=models.VectorParams(size=embedding_size, distance=self.distance_method),
                                        )
            return True 
        
        else :
            return False


    def insert_one(self, collection_name:str, text: str, vector: list,
                        metadata: dict = None,
                        record_id: str = None):
        if not self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        
        _ = self.client.upload_records(
            collection_name=collection_name, 
            records = [
                models.Record(
                    id = [record_id],
                    vector = vector,
                    payload = {
                        "text": text, "metadata": metadata
                    }
                )
            ],
        )
        return True


    def insert_many(self, collection_name:str, texts: list, vector: list,
                        metadata: list = None,
                        record_ids: list = None, batch_size: int = 50):

        
        if not self.is_collection_existed(collection_name = collection_name):
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        

        if metadata is None:
            metadata = [None]*len(texts)
        if record_ids is None:
            record_ids = list(range(len(texts)))

        
        for i in range(0, len(texts), batch_size):

            batch_vector = vector[i: (i + batch_size)]
            batch_texts = texts[i: (i + batch_size)]
            batch_metadata = metadata[i: (i + batch_size)]
            batch_record_ids = record_ids[i: (i + batch_size)]

            records_batch = [ models.Record(
                                            id = batch_record_ids[x],
                                            vector = batch_vector[x],
                                            payload = {
                                                "text": batch_texts[x], "metadata": batch_metadata[x]
                                            }
                                )
                             for x in range(len(batch_texts))  ]

            #we gonna insert batch by batch 

            try : 

                _ = self.client.upload_records(
                                                collection_name=collection_name, 
                                                records = records_batch
                                            )

            except Exception as e :
                self.logger.error(f"Error while inserting a batch : {e}")
                return False

        return True



    def search_by_vector(self, collection_name:str, vector: list, limit: int = 5):
        
        return self.client.search(
            collection_name = collection_name,
            query_vector = vector,
            limit = limit
        )    

    