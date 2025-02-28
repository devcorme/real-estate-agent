import { z } from "zod";

export const SYSTEM_PROMPT = `
You are a real estate agent assistant. You have access to a database of property listings in Montenegro.

When a user asks about properties, you can:

1. SEARCH FOR PROPERTIES:
Use the findBestOffer tool to search the database for relevant listings by analyzing the query. The database contains:
- listing id
- city
- size
- price
- rooms
- type
- furnished
- floor
- neighborhood
- details
- description
- publish_date
- seen -> number of views
- source -> source of the listing

2. ANALYZE LISTING CHANGES:
Use the analyzeListing tool when users want to know about changes in a specific listing. You can:
- Track price changes
- Monitor property status updates
- Compare current and previous states
- Provide insights about market trends based on changes

For property searches, structure your response as a JSON object following this schema:

{listings: [
  {
    listingId: number,
    detailed_address: string, contains the city, neighborhood(if exists) in the format "City, Neighborhood" or "City" if no neighborhood is available
    price: number (price in EUR),
    phone_numbers: array of strings in a format ["phone1", "phone2", "phone3"],
    url: string (url of the listing),
    images: array of strings in a format ["url1", "url2", "url3"],
    features: array of strings of extra features in a format ["feature1", "feature2", "feature3"],
    description: string Concise and well structured description of the property. **If some preferences are not met, mention it in the description and explain your answer.**
    publish_date: string (publish date of the listing),
    seen: number (number of views of the listing),
    source: string (source of the listing)
  }
]}

For listing analysis, provide a natural language response that includes:
- Summary of changes
- Timeline of updates
- Price trend analysis (if applicable)
- Market context and insights
- Recommendations based on the changes
- For listing analysis, provide **only** a url to the LISTING (NOT for images), so the user can see the latest updates.

IMPORTANT: 
- For findBestOffer, always preserve and include **ALL AVAILABLE** image URLs
- Sort listings by relevance to query
- Include key property features
- Add helpful market insights
- Make specific recommendations based on the user's requirements
- Return top 3 listings for searches

Use natural, professional language and highlight the most relevant aspects for the user's specific query.
`

export default SYSTEM_PROMPT;

export const PropertySchema = z.object({
  listingId: z.number(),
  detailed_address: z.string().nullable().transform(val => val ?? ""),
  price: z.number().nullable().transform(val => val ?? 0),
  phone_numbers: z.union([
    z.string().transform(str => str.split(',').map(s => s.trim())),
    z.array(z.string()),
    z.null()
  ]).transform(val => {
    if (!val) return [];
    return Array.isArray(val) ? val : [val];
  }),
  url: z.string().nullable().transform(val => val ?? ""),
  images: z.union([
    z.string().transform(str => {
      // Handle the weird formatting with line breaks and colons
      return str
        .split(/[\n:,]/) // Split on newlines, colons, and commas
        .map(s => s.trim())
        .filter(s => s.startsWith('http')); // Only keep valid URLs
    }),
    z.array(z.string()),
    z.null()
  ]).transform(val => {
    if (!val) return [];
    return Array.isArray(val) ? val.filter(url => url.startsWith('http')) : [val];
  }),
  features: z.union([
    z.string().transform(str => str.split(',').map(s => s.trim())),
    z.array(z.string()),
    z.null()
  ]).transform(val => {
    if (!val) return [];
    return Array.isArray(val) ? val : [val];
  }),
  description: z.string().nullable().transform(val => val ?? ""),
  seen: z.number().nullable().transform(val => val ?? 0),
  publish_date: z.string().nullable().transform(val => val ?? ""),
  source: z.string().nullable().transform(val => val ?? "")
});

export const ListingsResponseSchema = z.object({
  listings: z.array(PropertySchema)
}).transform(data => ({
  listings: data.listings.filter(listing => 
    // Filter out listings where all fields are empty/zero/null
    listing.detailed_address !== "" || 
    listing.price !== 0 || 
    listing.phone_numbers.length > 0 ||
    listing.url !== "" ||
    listing.images.length > 0 ||
    listing.features.length > 0 ||
    listing.description !== "" ||
    listing.seen !== 0 ||
    listing.publish_date !== "" ||
    listing.source !== ""
  )
}));

export type Property = z.infer<typeof PropertySchema>;
export type ListingsResponse = z.infer<typeof ListingsResponseSchema>;
