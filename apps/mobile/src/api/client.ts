export type ValidationResult = {
  status: "accepted" | "rejected" | "needs_clarification";
  reason_code: string;
  safe_to_process: boolean;
  food_relevance: "food" | "non_food" | "uncertain";
  moderation_flags: string[];
};

export type NutritionResponse = {
  estimated_calories: number;
  insights: string[];
  disclaimer: string;
  validation: ValidationResult;
};

export async function createMeal(payload: unknown): Promise<NutritionResponse> {
  const response = await fetch("http://localhost:8000/meals", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-user-id": "demo-user",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to create meal analysis.");
  }

  const data = await response.json();
  return {
    estimated_calories: data.analysis?.estimated_calories ?? 0,
    insights: data.analysis?.insights ?? [],
    disclaimer: data.disclaimer,
    validation: data.validation,
  };
}

