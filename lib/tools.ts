import { retrieveDocuments, retrieveListing } from "./retrieve-data";
import OpenAI from "openai";

import { ChatCompletionTool } from "openai/resources/chat/completions";

export interface SearchParams {
  city: string;
  query: string;
  minSize?: number;
  maxSize?: number;
  minPrice?: number;
  maxPrice?: number;
  rooms?: number;
  furnished?: boolean;
  floor?: number;
}

export const mainTools: ChatCompletionTool[] = [
  {
    type: "function",
    function: {
      name: "findBestOffer",
      description: "Search for real estate listings based on user criteria",
      parameters: {
        type: "object",
        properties: {
          city: {
            type: "string",
            description: "City name (e.g. Podgorica, Nikšić)",
          },
          query: {
            type: "string",
            description: "Optimized user query containing **all** information about the preferences in concise form.",
          },
          minSize: {
            type: "number",
            description: "Minimum size in square meters",
          },
          maxSize: {
            type: "number",
            description: "Maximum size in square meters",
          },
          minPrice: {
            type: "number",
            description: "Minimum price in EUR",
          },
          maxPrice: {
            type: "number",
            description: "Maximum price in EUR",
          },
          rooms: {
            type: "integer",
            description: "Least required number of rooms",
          },
          furnished: {
            type: "boolean",
            description: "Whether the property is furnished",
          },
          floor: {
            type: "integer",
            description: "Floor number (0 for ground floor)",
          }
        },
        required: ["city", "query"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "analyzeListing",
      description: "Use this tool to analyze changes in a listing and return a detailed description of the changes along with the current and previous states of the listing.",
      parameters: {
        type: "object",
        properties: {
          listingId: {
            type: "integer",
            description: "ID of the listing to analyze"
          }
        },
        required: ["listingId"]
      }
    }
  }
]; 

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