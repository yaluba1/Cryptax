# CrypTax
Free SaaS Solution to calculate taxes for crypto accounts.

## SaaS version

For now the SaaS version is free to use and you can get access by invitation. Send me an email if you want access.
I cannot make 100% open because services do cost money and I am a regular guy with small pockets. But I will eventually add a bitcoin, ethereum and solana wallet addresses for anyone who wants to contribute to keep this running.

The SaaS version is currently hosted in:

- Frontend: Cloudflare page.
- Backend: Currently at home using a Zerotrust Cloudflare tunnel. Will move it to a VM in Aruba Cloud in Italy as soon as it is estable.

### Alpha

Current support is limited to *Binance* and *Kraken* , which are the two I use. I will add others in future versions. You may help me with that, if you use other.

I opened my accounts in these crypto exchanges a few years back and I have quite a few transactions that DaLI/RP2 could not handle correctly (old cryptos, airdrops, etc). I need to look into this, because the result is not 100% correct. But for activity in the last couple of years and for major cryptos (BTC, ETH, SOL, etc.), it works well.

**URL**: [Cryptax](https://cryptax.yaluba.org) -> https://cryptax.yaluba.org

**Access**: by invitation only. Send me an email to *cryptax[at]yaluba[dot]com* if you want to try it. 

:radioactive: ***<span style="color:red">Use it at your own risk!!!</span>*** :radioactive:

Feel free to mount your own access using the instructions below.

# Frontend

The frontend is an SPA built using the [Quasar Framework](https://quasar.dev/) for [Vue](https://vuejs.org/)

For user authentication, I use the free tier of [Hanko](https://www.hanko.io/)

# Backend

Containerized with the following open SW components:

- [DaLI RP2](https://github.com/eprbell/dali-rp2)
- [FastAPI](https://fastapi.tiangolo.com/)
- [MariaDB](https://mariadb.org/)
- [MiniO](https://github.com/minio/minio) -> Not used yet
- [Redis](https://redis.io/)
- [RP2](https://github.com/eprbell/rp2)

