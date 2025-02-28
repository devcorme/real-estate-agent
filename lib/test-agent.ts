// 'use server';
import { askAssistant } from "./real-estate-agent";

async function main() {
    const response = await askAssistant("Find me a Flat in Kotor with 1 or more rooms and a price bellow 150k EUR");
    // const response = await askAssistant("Are there any updates for the listing with id 15?");
    console.log("Agent response:", response?.length ?? 0 ? response : "No response");
}

main().catch(console.error);