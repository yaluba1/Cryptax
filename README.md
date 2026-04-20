# CryptoTax
Free SaaS Solution to calculate taxes for crypto accounts.

## SaaS version

For now the SaaS version is free to use and you can get access by invitation. Send me an email if you want access.
I cannot make 100% open because services do cost money and I am a regular guy with small pockets. But I will eventually add a bitcoin, ethereum and solana wallet addresses for anyone who wants to contribute to keep this running.

The SaaS version is currently hosted in:

- Frontend: Cloudflare page.
- Backend: Aruba Cloud VMs in Italy.

I will provide the URL as soon as I have tested it properly and check that it is accurate with tax accountant (in Spain).

Feel free to mount your own access using the instructions below.

# Frontend

The frontend is an SPA built using the [Quasar Framework](https://quasar.dev/) for [Vue](https://vuejs.org/)

For user authentication, I use the free tier of [Hanko](https://www.hanko.io/)

# Backend

Containerized with the following open SW components:

- [DaLI RP2](https://github.com/eprbell/dali-rp2)
- [FastAPI](https://fastapi.tiangolo.com/)
- [MariaDB](https://mariadb.org/)
- [MiniO](https://github.com/minio/minio)
- [Redis](https://redis.io/)
- [RP2](https://github.com/eprbell/rp2)

