from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models.instrument import Instrument


INSTRUMENTS = [
    {
        "symbol": "NIFTY",
        "name": "NIFTY 50",
        "instrument_type": "INDEX",
    },
    {
        "symbol": "BANKNIFTY",
        "name": "NIFTY Bank",
        "instrument_type": "INDEX",
    },
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "instrument_type": "STOCK",
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank",
        "instrument_type": "STOCK",
    },
    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank",
        "instrument_type": "STOCK",
    },
    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "instrument_type": "STOCK",
    },
    {
        "symbol": "INFY",
        "name": "Infosys",
        "instrument_type": "STOCK",
    },
    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services",
        "instrument_type": "STOCK",
    },
]


def seed_instruments():
    db = SessionLocal()

    try:
        for instrument_data in INSTRUMENTS:
            existing = db.scalar(
                select(Instrument).where(
                    Instrument.symbol == instrument_data["symbol"]
                )
            )

            if existing is None:
                db.add(Instrument(**instrument_data))

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed_instruments()
    print("Instruments seeded successfully.")