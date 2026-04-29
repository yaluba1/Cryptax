import { z } from 'zod';

export const CountryEnum = z.enum(['IE', 'JP', 'ES', 'US', 'GENERIC']);
export const ExchangeEnum = z.enum(['binance', 'kraken', 'coinbase']);
export const AccountingMethodEnum = z.enum(['FIFO', 'LIFO', 'HIFO', 'LOFO']);

export const GenericInfoSchema = z.object({
  long_term_capital_gains_days: z.number().int().min(0).default(365),
  accounting_method: AccountingMethodEnum.default('FIFO'),
});

export const JobRequestSchema = z.object({
  lang: z.string().length(2).default('en'),
  country: CountryEnum,
  generic: GenericInfoSchema.nullable().optional(),
  exchange: ExchangeEnum,
  year: z.number().int().max(new Date().getFullYear()),
  account_holder: z.string().email(),
  uid: z.string(),
  api_key: z.string().min(1),
  api_secret: z.string().min(1),
  fiat: z.string().length(3),
}).refine((data) => {
  if (data.country === 'GENERIC' && !data.generic) {
    return false;
  }
  return true;
}, {
  message: "Generic information is required when country is GENERIC",
  path: ["generic"],
});

export type JobRequest = z.infer<typeof JobRequestSchema>;
