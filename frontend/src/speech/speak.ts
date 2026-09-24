const VOICE_KEY = "eir_voice_enabled";

type SpeakHooks = {
  onStart?: () => void;
  onEnd?: () => void;
};

let generation = 0;
let keepAlive = 0;

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function voiceEnabled(): boolean {
  if (!canSpeak()) return false;
  const stored = localStorage.getItem(VOICE_KEY);
  if (stored === null) return true;
  return stored === "1";
}

export function setVoiceEnabled(on: boolean): void {
  localStorage.setItem(VOICE_KEY, on ? "1" : "0");
  if (!on) stopSpeaking();
}

export function welcomeText(name?: string | null): string {
  const who = name?.trim();
  const hello = who ? `Bonjour ${who}.` : "Bonjour.";
  return (
    `${hello} Ici EIR, la pharmacie de bord. ` +
    "Decris ce que tu ressens. " +
    "Je verifie ton profil, tes allergies et le stock avant de te repondre."
  );
}

export function stopSpeaking(): void {
  generation += 1;
  if (keepAlive) {
    window.clearInterval(keepAlive);
    keepAlive = 0;
  }
  if (canSpeak()) window.speechSynthesis.cancel();
}

export function primeSpeech(): void {
  if (!canSpeak() || !voiceEnabled()) return;
  window.speechSynthesis.resume();
}

const SPEECH_REPLACEMENTS: Array<[RegExp, string]> = [
  [/Matricaria chamomilla/gi, "camomille"],
  [/Cinchona officinalis/gi, "quinquina"],
  [/Plantago major/gi, "plantain"],
  [/Artemisia annua/gi, "armoise"],
  [/Calendula officinalis/gi, "souci"],
  [/Aloe vera/gi, "aloès"],
  [/10-15 min/gi, "dix à quinze minutes"],
  [/\bcalendula\b/gi, "souci"],
  [/\baloes\b/gi, "aloès"],
  [/\bpenicillium\b/gi, "pénicillium"],
  [/\bparacetamol\b/gi, "paracétamol"],
  [/\bibuprofene\b/gi, "ibuprofène"],
  [/\bibuprofen\b/gi, "ibuprofène"],
  [/\bondansetron\b/gi, "ondansétron"],
  [/\bmeclizine\b/gi, "méclizine"],
  [/\bloperamide\b/gi, "lopéramide"],
  [/\bomeprazole\b/gi, "oméprazole"],
  [/\bazithromycine\b/gi, "azithromycine"],
  [/\bamoxicilline\b/gi, "amoxicilline"],
  [/\bwarfarine\b/gi, "warfarine"],
  [/\brehydration\b/gi, "réhydratation"],
  [/\bdeshydratation\b/gi, "déshydratation"],
  [/\bYggdrasil\b/gi, "Igdrassil"],
  [/\bOllama\b/gi, "Olama"],
  [/\bMQTT\b/g, "M. Q. T. T."],
  [/\bSpO2\b/gi, "saturation"],
  [/\bAINS\b/g, "anti-inflammatoires"],
  [/\bEIR\b/g, "E. I. R."],
  [/\bJSON\b/g, "décision"],
  [/\bmg\b/gi, "milligrammes"],
  [/\bprecisement\b/gi, "précisément"],
  [/\bprecis\b/gi, "précis"],
  [/\birritee\b/gi, "irritée"],
  [/\bdecoction\b/gi, "décoction"],
  [/\bsommites\b/gi, "sommités"],
  [/\bmedicament\b/gi, "médicament"],
  [/\bmedicaux\b/gi, "médicaux"],
  [/\bmedicale\b/gi, "médicale"],
  [/\bmedical\b/gi, "médical"],
  [/\bdemangeaisons\b/gi, "démangeaisons"],
  [/\bintensite\b/gi, "intensité"],
  [/\bappetit\b/gi, "appétit"],
  [/\bregulierement\b/gi, "régulièrement"],
  [/\bnausees\b/gi, "nausées"],
  [/\bdiarrhee\b/gi, "diarrhée"],
  [/\bbrulure\b/gi, "brûlure"],
  [/\bfievre\b/gi, "fièvre"],
  [/\btiede\b/gi, "tiède"],
  [/\bserieux\b/gi, "sérieux"],
  [/\bepisode\b/gi, "épisode"],
  [/\bevolue\b/gi, "évolue"],
  [/\bgorgees\b/gi, "gorgées"],
  [/\bassocies\b/gi, "associés"],
  [/\bassociee\b/gi, "associée"],
  [/\banalgesique\b/gi, "analgésique"],
  [/\bdefaut\b/gi, "défaut"],
  [/\becrans\b/gi, "écrans"],
  [/\blegere\b/gi, "légère"],
  [/\bmolecule\b/gi, "molécule"],
  [/\bverifie\b/gi, "vérifie"],
  [/\brepondre\b/gi, "répondre"],
  [/\bdecris\b/gi, "décris"],
  [/\btete\b/gi, "tête"],
  [/\bca\b/gi, "ça"],
  [/dis-moi ou\b/gi, "dis-moi où"],
];

export function prepareSpeech(text: string): string {
  let spoken = text;
  for (const [pattern, replacement] of SPEECH_REPLACEMENTS) {
    spoken = spoken.replace(pattern, replacement);
  }
  return spoken.replace(/\s+/g, " ").trim();
}

function frenchVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  const french = voices.filter((voice) => voice.lang.toLowerCase().startsWith("fr"));
  const preferred = ["hortense", "denise", "julie", "audrey", "thomas", "paul"];
  for (const name of preferred) {
    const match = french.find((voice) => voice.name.toLowerCase().includes(name));
    if (match) return match;
  }
  return french[0] ?? null;
}

export function speak(text: string, hooks?: SpeakHooks): void {
  if (!canSpeak() || !voiceEnabled()) {
    hooks?.onEnd?.();
    return;
  }
  const clean = prepareSpeech(text);
  if (!clean) {
    hooks?.onEnd?.();
    return;
  }
  const mine = generation + 1;
  generation = mine;
  if (keepAlive) {
    window.clearInterval(keepAlive);
    keepAlive = 0;
  }
  window.speechSynthesis.cancel();

  const start = () => {
    if (mine !== generation) return;
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "fr-FR";
    utterance.rate = 0.92;
    const voice = frenchVoice();
    if (voice) utterance.voice = voice;
    utterance.onstart = () => {
      if (mine !== generation) return;
      hooks?.onStart?.();
      keepAlive = window.setInterval(() => {
        if (!window.speechSynthesis.speaking) {
          window.clearInterval(keepAlive);
          keepAlive = 0;
          return;
        }
        window.speechSynthesis.pause();
        window.speechSynthesis.resume();
      }, 10000);
    };
    utterance.onend = () => {
      if (mine !== generation) return;
      if (keepAlive) {
        window.clearInterval(keepAlive);
        keepAlive = 0;
      }
      hooks?.onEnd?.();
    };
    utterance.onerror = () => {
      if (mine !== generation) return;
      hooks?.onEnd?.();
    };
    window.speechSynthesis.speak(utterance);
  };

  if (window.speechSynthesis.getVoices().length > 0) {
    window.setTimeout(start, 60);
    return;
  }
  const onVoices = () => {
    window.speechSynthesis.removeEventListener("voiceschanged", onVoices);
    start();
  };
  window.speechSynthesis.addEventListener("voiceschanged", onVoices);
  window.speechSynthesis.getVoices();
}
