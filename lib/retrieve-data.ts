import { cosineDistance, asc, sql} from "drizzle-orm";
import { generateEmbedding } from "./generate-embedding";
import { db } from "./db";
import { listings, listingHistory } from "./db/schema";
import { SearchParams } from "./tools";

process.removeAllListeners('warning');


export async function retrieveDocuments(params: SearchParams, limit = 5) {
  const embeddings = await generateEmbedding(params.query);
  const similarity = sql<number>`${cosineDistance(listings.embedding, embeddings)}`;

  const conditions = [];
  
  if (params.city) conditions.push(sql`(city = ${params.city} OR city IS NULL)`);
  if (params.minSize) conditions.push(sql`(size >= ${params.minSize} OR size IS NULL)`);
  if (params.maxSize) conditions.push(sql`(size <= ${params.maxSize} OR size IS NULL)`);
  if (params.minPrice) conditions.push(sql`(price >= ${params.minPrice} OR price IS NULL)`);
  if (params.maxPrice) conditions.push(sql`(price <= ${params.maxPrice} OR price IS NULL)`);
  if (params.rooms) conditions.push(sql`(rooms >= ${params.rooms} OR rooms IS NULL)`);
  if (params.furnished) conditions.push(sql`(furnished = ${params.furnished} OR furnished IS NULL)`);
  if (params.floor) conditions.push(sql`(floor = ${params.floor} OR floor IS NULL)`);

  const documents = await db.query.listings.findMany({
    where: conditions.length ? sql`${sql.join(conditions, sql` AND `)}` : undefined,
    orderBy: asc(similarity),
    limit: limit
  });

  console.log("Total retrieved documents:", documents.length);
  return documents;
}

interface ListingHistory {
  id: number;
  listing_id: number;
  updated_at: Date;
  change_description: string;
}

interface ListingWithHistory {
  listing: typeof listings.$inferSelect;
  history: ListingHistory[];
}

export async function retrieveListing(listingId: number): Promise<ListingWithHistory> {
  const listing = await db.query.listings.findFirst({
    where: sql`id = ${listingId}`
  });

  if (!listing) {
    throw new Error(`Listing with ID ${listingId} not found`);
  }

  const history = await db.select()
    .from(listingHistory)
    .where(sql`listing_id = ${listingId}`)
    .orderBy(sql`updated_at desc`);

  return {
    listing,
    history: history as ListingHistory[]
  };
}

// retrieveDocuments("Tell me about flats in Podgorica");