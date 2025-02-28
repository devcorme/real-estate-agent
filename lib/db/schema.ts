import { index, pgTable, serial, text, timestamp, numeric, jsonb, varchar, vector, integer, boolean } from 'drizzle-orm/pg-core';

export const listings = pgTable('listings', {
  id: serial('id').primaryKey(),
  createdAt: timestamp('created_at').notNull(),
  updatedAt: timestamp('updated_at').notNull(),
  city: text('city'),
  size: numeric('size'),  // Float in SQLAlchemy maps to real in Postgres
  price: numeric('price'), // Changed from numeric to real to match Python Float
  rooms: integer('rooms'),
  type: text('type'),
  furnished: boolean('furnished'),
  floor: integer('floor'),
  neighborhood: text('neighborhood'),
  details: jsonb('details'),
  description: text('description'),
  phoneNumbers: text('phone_numbers').array(),
  images: text('images').array(),
  url: varchar('url').unique(),
  embedding: vector("embedding", { dimensions: 256 }),
  publish_date: text('publish_date'),
  seen: integer('seen'),
  source: text('source'),
},
(table) => ({
  embeddingIndex: index("embedding_index").using(
    "hnsw",
    table.embedding.op("vector_cosine_ops")
  ),
}));

export const listingHistory = pgTable('listing_history', {
  id: serial('id').primaryKey(),
  listing_id: integer('listing_id')
    .references(() => listings.id, { onDelete: 'cascade' })
    .notNull(),
  updated_at: timestamp('updated_at').notNull().defaultNow(),
  change_description: text('change_description').notNull()
});