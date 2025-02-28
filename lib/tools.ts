// 'use server';
import { retrieveDocuments, retrieveListing } from "./retrieve-data";
import OpenAI from "openai";
import { SearchParams, mainTools } from "./types";

export { mainTools };

export async function findBestOffer(params: SearchParams) {
   return await retrieveDocuments(params);
}

export async function analyzeListing(listingId: number) {
  try {
    const listingData = await retrieveListing(listingId);
    const client = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
  
    const response = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: "You are an expert in analyzing real estate listings. Your task is to analyze the changes in a listing and return a detailed description of the changes."
        },
        {
          role: "user",
          content: JSON.stringify({
            listing: listingData.listing,
            changes: listingData.history.map(h => ({
              date: h.updated_at,
              changes: h.change_description
            }))
          })
        }
      ]
    });
  
    const analysis = response.choices[0]?.message?.content || 'No analysis available';
    return {
      listing: listingData.listing,
      history: listingData.history,
      analysis
    };
  } catch (error) {
    return {
      error: error
    }
  }
}