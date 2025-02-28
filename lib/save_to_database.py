import os
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, TIMESTAMP, ARRAY, Boolean, Text, Float, text
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from openai import OpenAI
import json

# Load environment variables
load_dotenv('.env.local')

database_url = os.getenv('DATABASE_URL')
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

if not database_url:
    raise Exception("DATABASE_URL is not set")

# Initialize SQLAlchemy
engine = create_engine(database_url)
metadata = MetaData()

# First create vector extension
with engine.connect() as conn:
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
    conn.commit()

# Drop existing table and index if they exist
# with engine.connect() as conn:
#     conn.execute(text('DROP TABLE IF EXISTS listings CASCADE;'))
#     conn.commit()

# Define and create table
listings_table = Table(
    'listings',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('created_at', TIMESTAMP, nullable=False),
    Column('updated_at', TIMESTAMP, nullable=False),
    Column('city', Text),
    Column('size', Float),
    Column('price', Float),
    Column('rooms', Integer),
    Column('type', Text),
    Column('furnished', Boolean),
    Column('floor', Integer),
    Column('neighborhood', Text),
    Column('details', JSONB),
    Column('description', Text),
    Column('phone_numbers', ARRAY(String)),
    Column('images', ARRAY(String)),
    Column('url', String, unique=True),
    Column('embedding', Vector(256)),
    Column('publish_date', String),
    Column('seen', Integer),
    Column('source', String)
)

# Add this after listings_table definition
listing_history_table = Table(
    'listing_history',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('listing_id', Integer, nullable=False),
    Column('updated_at', TIMESTAMP, nullable=False),
    Column('change_description', Text, nullable=False),
)

metadata.create_all(engine)

# Now create the index after table is created
with engine.connect() as conn:
    conn.execute(text('''
    CREATE INDEX IF NOT EXISTS data_embedding_index 
    ON listings 
    USING hnsw (embedding vector_cosine_ops);
    '''))
    conn.commit()

# Add trigger function and trigger
with engine.connect() as conn:
    conn.execute(text('''
    CREATE OR REPLACE FUNCTION log_listing_changes()
    RETURNS TRIGGER AS $$
    DECLARE
        changes text[];
        change_desc text;
    BEGIN
        changes := ARRAY[]::text[];
        
        IF OLD.publish_date IS DISTINCT FROM NEW.publish_date THEN
            changes := array_append(changes, CASE 
                WHEN OLD.publish_date IS NULL OR OLD.publish_date = '' THEN 'Publish date was added: ' || NEW.publish_date
                WHEN NEW.publish_date IS NULL OR NEW.publish_date = '' THEN 'Publish date was removed: ' || OLD.publish_date
                ELSE format('Publish date changed from %s to %s', OLD.publish_date, NEW.publish_date)
            END);
        END IF;
        
        IF OLD.city IS DISTINCT FROM NEW.city THEN
            changes := array_append(changes, CASE 
                WHEN OLD.city IS NULL OR OLD.city = '' THEN 'City was added: ' || NEW.city
                WHEN NEW.city IS NULL OR NEW.city = '' THEN 'City was removed: ' || OLD.city
                ELSE format('City changed from %s to %s', OLD.city, NEW.city)
            END);
        END IF;
        
        IF OLD.size IS DISTINCT FROM NEW.size THEN
            changes := array_append(changes, CASE 
                WHEN OLD.size IS NULL THEN format('Size was added: %s m²', round(NEW.size::numeric, 2))
                WHEN NEW.size IS NULL THEN format('Size was removed: %s m²', round(OLD.size::numeric, 2))
                ELSE format('Size changed from %s m² to %s m²', round(OLD.size::numeric, 2), round(NEW.size::numeric, 2))
            END);
        END IF;
        
        IF OLD.price IS DISTINCT FROM NEW.price THEN
            changes := array_append(changes, CASE 
                WHEN OLD.price IS NULL THEN format('Price was added: %s €', round(NEW.price::numeric, 2))
                WHEN NEW.price IS NULL THEN format('Price was removed: %s €', round(OLD.price::numeric, 2))
                ELSE format('Price changed from %s € to %s €', round(OLD.price::numeric, 2), round(NEW.price::numeric, 2))
            END);
        END IF;
        
        IF OLD.rooms IS DISTINCT FROM NEW.rooms THEN
            changes := array_append(changes, CASE 
                WHEN OLD.rooms IS NULL THEN format('Rooms count was added: %s', NEW.rooms)
                WHEN NEW.rooms IS NULL THEN format('Rooms count was removed: %s', OLD.rooms)
                ELSE format('Rooms changed from %s to %s', OLD.rooms, NEW.rooms)
            END);
        END IF;
        
        IF OLD.type IS DISTINCT FROM NEW.type THEN
            changes := array_append(changes, CASE 
                WHEN OLD.type IS NULL OR OLD.type = '' THEN 'Type was added: ' || NEW.type
                WHEN NEW.type IS NULL OR NEW.type = '' THEN 'Type was removed: ' || OLD.type
                ELSE format('Type changed from %s to %s', OLD.type, NEW.type)
            END);
        END IF;
        
        IF OLD.furnished IS DISTINCT FROM NEW.furnished THEN
            changes := array_append(changes, CASE 
                WHEN OLD.furnished IS NULL THEN format('Furnished status was added: %L', NEW.furnished)
                WHEN NEW.furnished IS NULL THEN format('Furnished status was removed: %L', OLD.furnished)
                ELSE format('Furnished status changed from %L to %L', OLD.furnished, NEW.furnished)
            END);
        END IF;
        
        IF OLD.floor IS DISTINCT FROM NEW.floor THEN
            changes := array_append(changes, CASE 
                WHEN OLD.floor IS NULL THEN format('Floor was added: %s', NEW.floor)
                WHEN NEW.floor IS NULL THEN format('Floor was removed: %s', OLD.floor)
                ELSE format('Floor changed from %s to %s', OLD.floor, NEW.floor)
            END);
        END IF;
        
        IF OLD.neighborhood IS DISTINCT FROM NEW.neighborhood THEN
            changes := array_append(changes, CASE 
                WHEN OLD.neighborhood IS NULL OR OLD.neighborhood = '' THEN format('Neighborhood was added: %s', NEW.neighborhood)
                WHEN NEW.neighborhood IS NULL OR NEW.neighborhood = '' THEN format('Neighborhood was removed: %s', OLD.neighborhood)
                ELSE format('Neighborhood changed from %s to %s', OLD.neighborhood, NEW.neighborhood)
            END);
        END IF;
        
        IF OLD.details IS DISTINCT FROM NEW.details THEN
            changes := array_append(changes, CASE 
                WHEN OLD.details IS NULL THEN format('Details were added: %s', NEW.details::text)
                WHEN NEW.details IS NULL THEN format('Details were removed: %s', OLD.details::text)
                ELSE format('Details were updated: %s', NEW.details::text)
            END);
        END IF;
        
        IF OLD.description IS DISTINCT FROM NEW.description THEN
            changes := array_append(changes, CASE 
                WHEN OLD.description IS NULL OR OLD.description = '' THEN format('Description was added: %s', NEW.description)
                WHEN NEW.description IS NULL OR NEW.description = '' THEN format('Description was removed: %s', OLD.description)
                ELSE format('Description changed from %s to %s', OLD.description, NEW.description)
            END);
        END IF;
        
        IF OLD.phone_numbers IS DISTINCT FROM NEW.phone_numbers THEN
            changes := array_append(changes, 'Phone numbers were changed');
        END IF;
        
        IF OLD.images IS DISTINCT FROM NEW.images THEN
            changes := array_append(changes, 'Images were changed');
        END IF;
        
        IF array_length(changes, 1) > 0 THEN
            change_desc := array_to_string(changes, '; ');
            INSERT INTO listing_history (listing_id, updated_at, change_description)
            VALUES (NEW.id, CURRENT_TIMESTAMP, change_desc);
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    '''))
    
    # Create trigger
    conn.execute(text('''
    DROP TRIGGER IF EXISTS listing_changes_trigger ON listings;
    CREATE TRIGGER listing_changes_trigger
    AFTER UPDATE ON listings
    FOR EACH ROW
    EXECUTE FUNCTION log_listing_changes();
    '''))
    conn.commit()

def get_embedding(text: str) -> List[float]:
    # return [0.0] * 256
    response = client.embeddings.create(
        model="text-embedding-3-small",
        dimensions=256,
        input=text
    )
    return response.data[0].embedding

def check_duplicates(conn, embedding: List[float], raw_text: str) -> tuple[List[Dict], str]:
    # Query similar listings using vector cosine distance
    query = f'''
        SELECT 
            id, url, price, size, rooms, type, furnished, floor, 
            neighborhood, details, description, phone_numbers,
            1 - (embedding <-> array{embedding}::vector) as similarity
        FROM listings 
        WHERE embedding <-> array{embedding}::vector < 0.2
        ORDER BY (embedding <-> array{embedding}::vector) ASC
    '''
    similar_listings = conn.execute(text(query)).fetchall()
    
    if not similar_listings:
        return [], """VERDICT: [NOT_DUPLICATE]
SIMILAR_LISTINGS: None
ANALYSIS: No similar listings found in the database."""

    # Prepare messages for AI evaluation
    messages = [
        {"role": "system", "content": """You are a duplicate listing detector. Compare the new listing with existing ones and determine if they are duplicates.
        A listing is considered duplicate if:
        - Same property with very similar or identical characteristics (price, size, rooms, etc.)
        - Same phone numbers
        - Very similar description
        - Also consider that some flats are yet to be built, so there can be multiple listings for the same property, with similar descriptions. Those will probably be managed by the same real estate agent.

        Please provide your analysis in the following format:
        VERDICT: [DUPLICATE/NOT_DUPLICATE]
        SIMILAR_LISTINGS: [List URLs of potential duplicates with their similarity scores]
        ANALYSIS: [Brief explanation of why you think these are duplicates or not]"""},
        {"role": "user", "content": f"New listing:\n{raw_text}\n\nPotential duplicates:\n"}
    ]
    
    for listing in similar_listings:
        listing_details = {
            'id': listing.id,
            'url': listing.url,
            'price': listing.price,
            'size': listing.size,
            'rooms': listing.rooms,
            'type': listing.type,
            'furnished': listing.furnished,
            'floor': listing.floor,
            'neighborhood': listing.neighborhood,
            'details': listing.details,
            'description': listing.description,
            'phone_numbers': listing.phone_numbers,
            'similarity': listing.similarity
        }
        messages[1]["content"] += f"\nListing {listing.id} ({listing.url}):\n{json.dumps(listing_details, indent=2)}\n"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0
    )
    
    agent_response = response.choices[0].message.content
    is_duplicate = "duplicate" in agent_response.lower()
    
    return (similar_listings if is_duplicate else [], agent_response)

def save_listing(data: Dict, url: str, auto_control: bool=False) -> int:
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            now = datetime.now()
            
            raw_text = '\n'.join(f'{k}-{v}' for k,v in data.items() if v is not None)
            embedding = get_embedding(raw_text)
            
            listing_data = {
                'created_at': now,
                'updated_at': now,
                'city': data.get('city', None),
                'size': data.get('size', None),
                'price': data.get('price', None),
                'rooms': data.get('rooms', None),
                'type': data.get('type', None),
                'furnished': data.get('furnished', None),
                'floor': data.get('floor', None),
                'neighborhood': data.get('neighborhood', None),
                'details': data.get('short_description', {}),
                'description': data.get('title', '') + '\n\n' + '\n'.join(data.get('detailed_description', [])),
                'phone_numbers': data.get('phone_numbers', []),
                'images': data.get('images', []),
                'url': url,
                'embedding': embedding,
                'publish_date': data.get('publish_date', None),
                'seen': data.get('seen', 0),
                'source': data.get('source', None)
            }

            # First check if record exists
            result = conn.execute(
                listings_table.select().where(listings_table.c.url == url)
            ).first()

            if result is not None:
                listing_id = result.id
                listing_data.pop('created_at')  # Don't update creation time
                conn.execute(
                    listings_table.update()
                    .where(listings_table.c.url == url)
                    .values(**listing_data)
                )
                trans.commit()
                return listing_id

            # If it's a new listing, check for duplicates
            duplicates, agent_analysis = check_duplicates(conn, embedding, raw_text)
            agent_verdict = agent_analysis.lower()
            
            if auto_control and len(duplicates) > 0:
                if ("verdict: duplicate" in agent_verdict or "verdict: [duplicate]" in agent_verdict):
                    print(f"🚫 Auto-skipping duplicate listing: {url}")
                    print(f"Agent analysis: {agent_analysis}")
                    trans.rollback()
                    return None
                elif ("verdict: not_duplicate" in agent_verdict or "verdict: [not_duplicate]" in agent_verdict):
                    print(f"✅ Auto-saving non-duplicate listing: {url}")
                    print(f"Agent analysis: {agent_analysis}")
                    result = conn.execute(
                        listings_table.insert().values(**listing_data)
                        .returning(listings_table.c.id)
                    )
                    listing_id = result.scalar()
                    trans.commit()
                    return listing_id
                else:
                    print(f"⚠ Auto-control: Unclear verdict from agent. Defaulting to manual review.")
            
            # Manual review process only if duplicates exist
            if len(duplicates) > 0:
                print("\nAgent Analysis:")
                print(agent_analysis)
                print("\nPotential duplicates found:")
                for d in duplicates:
                    print(f"- {d.url} (similarity: {d.similarity:.3f})")
                
                while True:
                    user_input = input("\nDo you want to save this listing anyway? (yes/no): ").lower().strip()
                    if user_input in ['yes', 'no']:
                        break
                    print("Please answer with 'yes' or 'no'")

                if user_input == 'no':
                    print("Skipping listing insertion.")
                    trans.rollback()
                    return None

            # Insert new listing
            result = conn.execute(
                listings_table.insert().values(**listing_data)
                .returning(listings_table.c.id)
            )
            listing_id = result.scalar()
            trans.commit()
            return listing_id
            
        except Exception as e:
            trans.rollback()
            raise e
