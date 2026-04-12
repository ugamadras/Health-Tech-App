export async function createMeal(payload) {
    var _a, _b, _c, _d;
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
        estimated_calories: (_b = (_a = data.analysis) === null || _a === void 0 ? void 0 : _a.estimated_calories) !== null && _b !== void 0 ? _b : 0,
        insights: (_d = (_c = data.analysis) === null || _c === void 0 ? void 0 : _c.insights) !== null && _d !== void 0 ? _d : [],
        disclaimer: data.disclaimer,
        validation: data.validation,
    };
}
