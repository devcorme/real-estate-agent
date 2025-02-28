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