export interface Country {
  code: string
  name: string
  latitude: number
  longitude: number
}

export interface CountryUploadStat {
  countryCode: string
  countryName: string
  uploads: number
}
