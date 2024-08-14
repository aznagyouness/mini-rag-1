from .enums.DataBaseEnum import DataBaseEnum
from .BaseDataModel import BaseDataModel
from .db_schemas.data_chunk import DataChunk
from bson.objectid import ObjectID
from pymongo import InsertOne


class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]


    async def create_chunk(self, chunk :DataChunk ):

        result = await self.collection.insert_one(chunk.dict())
        chunk._id = result.inserted_id

        return chunk
    
    
    async def get_chunk(self, chunk_id:str ):

        result = self.collection.find(
            {'_id':ObjectID(chunk_id) }
        )

        if result is None :
            return None 
        
        return DataChunk(**result)
    

    async def insert_many_chunks(self, chunks: list, batch_size: int=100):

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+100]

            operations = [
                InsertOne(chunk) for chunk in batch
            ]

            await self.collection.bulk_write(operations)

        return len(chunks)
    


        
