import dotenv from "dotenv";
import OpenAI from "openai";
import { SYSTEM_PROMPT, ListingsResponseSchema } from "./prompt-schema";
import { mainTools, findBestOffer, analyzeListing } from "./tools";
import { ChatCompletionMessageParam } from "openai/resources/chat/completions";
dotenv.config({ path: ".env.local" });

process.removeAllListeners("warning");

const openai = new OpenAI({
    apiKey : process.env.OPENAI_API_KEY || 'dummy-key' 
});

const LLM_MODEL = process.env.LLM_MODEL;

export async function askAssistant(prompt: string) {
    try {
        const conversation: ChatCompletionMessageParam[] = [
            { role: "system", content: SYSTEM_PROMPT },
            { role: "user", content: prompt }
        ];
        
        const response = await openai.chat.completions.create({
            model: LLM_MODEL as string,
            messages: conversation,
            tools: mainTools,
            tool_choice: "auto",
        });
        
        if (!response.choices?.[0]?.message) {
            return [];
        }

        const message = response.choices[0].message;
        if (!message.tool_calls) {
            return message.content;
        }

        const toolCall = message.tool_calls[0];
        const toolArgs = JSON.parse(toolCall.function.arguments);
        
        if (toolCall.function.name === 'findBestOffer') {
            console.log("Calling findBestOffer with args:", toolArgs);
            const rawListings = await findBestOffer(toolArgs);

            // console.log(rawListings[0]);

            const finalResponse = await openai.chat.completions.create({
                model: LLM_MODEL as string,
                messages: [
                    ...conversation,
                    { 
                        role: "assistant", 
                        content: "I'll search for properties that match your criteria. And answer in the language of the query."
                    },
                    {
                        role: "function",
                        name: "findBestOffer",
                        content: JSON.stringify(rawListings)
                    }
                ],
                response_format: { type: "json_object" }
            });

            if (!finalResponse.choices?.[0]?.message?.content) {
                return [];
            }

            // console.log("LLM Response:", finalResponse.choices[0].message.content);

            const parsedResponse = ListingsResponseSchema.parse(
                JSON.parse(finalResponse.choices[0].message.content)
            );
            return parsedResponse.listings;
        } 
        
        if (toolCall.function.name === 'analyzeListing') {
            console.log("Calling analyzeListing with args:", toolArgs);
            const analysis = await analyzeListing(toolArgs.listingId);

            const finalResponse = await openai.chat.completions.create({
                model: LLM_MODEL as string,
                messages: [
                    ...conversation,
                    {
                        role: "function",
                        name: "analyzeListing",
                        content: JSON.stringify(analysis)
                    }
                ]
            });

            return finalResponse.choices[0]?.message?.content || "No analysis available";
        }
    } catch (error) {
        console.error(error);
        throw new Error("An error occurred while asking the assistant");
    }
}


