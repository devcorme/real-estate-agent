// this scraper is deprecated, but I'm keeping it here for reference
import FireCrawlApp from '@mendable/firecrawl-js';
import { z } from 'zod';
// import dotenv from 'dotenv';


// dotenv.config({ path: ".env.local" });

const app = new FireCrawlApp({apiKey: process.env.FIRECRAWL_API_KEY as string});

const schema = z.object({
  apartments: z.array(z.object({
    city: z.string(),
    price: z.string(),
    square_meters: z.string(),
    distance_from_center: z.string(),
    furnished: z.string(),
    rooms: z.string(),
    floor: z.string(),
    total_floors: z.string(),
    has_elevator: z.boolean(),
    description: z.string(),
    address: z.string(),
    link: z.string().optional()
  }))
});

export async function scrapeApartments(city: string) {
  const extractResult = await app.extract([
    `https://patuljak.me/c/stanovi/grad-${city}/namjena-prodaja`
  ], {
    prompt: "Extract the 5 most recent apartments with details including city, price, square meters, distance from center, furnished status, number of rooms, floor, total floors, has elevator, description, address and link to the advert. Only include ones for sale.",
    schema,
  });
  
  console.log(JSON.stringify(extractResult, null, 2));
  if ('data' in extractResult) {
    console.log('Apartments:', JSON.stringify(extractResult.data.apartments, null, 2));
  }
  return extractResult;
}

scrapeApartments("Podgorica");