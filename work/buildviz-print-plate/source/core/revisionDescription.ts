import { normalizeVersionMessage } from './buildModel'

/** A revision description is a short human explanation, not a generated ID. */
export const requireRevisionDescription = (raw: unknown): string => {
  const message = normalizeVersionMessage(raw)
  const generic = /^(?:(?:update|updated|regenerate|regenerated|rebuild|rebuilt|publish|published|push|pushed|test|testing|changes?|fix|fixed|new|latest|version|revision|build|scene|model|geometry|cad|snapshot|main|v\d+|r\d+)[\s.,:_-]*)+$/i
  if (!message || message.length < 12 || !/\S+\s+\S+/.test(message) || generic.test(message)) {
    throw new Error(
      'Describe this revision in one or two sentences: what changed and why. ' +
      'Pass --message (or message in the API), for example: "Add yaw-horn access holes so the screws can be tightened with the hip servo installed." ' +
      'A version number or a generic message such as "update" or "regenerate" is not a description.',
    )
  }
  return message
}
