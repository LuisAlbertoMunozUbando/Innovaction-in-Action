export type Language = 'en'|'es'|'fr'|'zh'|'ja'|'ru'|'ko'|'de'|'ar'|'he';
export type InnovationRequest = { language:Language; objective:string; organization?:string; audience?:string; durationMinutes:number; participants:number; maturity?:string; constraints?:string; };
export type Activity = { title:string; minutes:number; purpose:string; instructions:string[]; output:string; sourceTags?:string[]; };
export type InnovationPlan = { title:string; objective:string; rationale:string; activities:Activity[]; materials:string[]; metrics:string[]; risks:string[]; nextSteps:string[]; references?:string[]; };
