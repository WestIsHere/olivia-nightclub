import discord

CARS = {
    "audi_rs3": {
        "name": "Audi RS3",
        "price": 30_000,
    },
    "bmw_m5": {
        "name": "BMW M5",
        "price": 50_000,
    },
    "audi_rs6": {
        "name": "Audi RS6",
        "price": 75_000,
    },
    "porsche_911": {
        "name": "Porsche 911",
        "price": 150_000,
    },
    "class_g": {
        "name": "Class G",
        "price": 250_000,
    },
    "urus": {
        "name": "Lamborghini URUS",
        "price": 350_000,
    },
    "svj": {
        "name": "Lamborghini SVJ",
        "price": 500_000,
    },
    "laferrari": {
        "name": "LaFerrari",
        "price": 1_000_000,
    },
    "centenario": {
        "name": "Lamborghini Centenario",
        "price": 2_000_000,
    },
}

WATCHES = {
    "day_date": {
        "name": "Rolex Day-Date",
        "price": 50_000,
    },
    "daytona": {
        "name": "Rolex Daytona",
        "price": 150_000,
    },
    "ap_royal": {
        "name": "Audemars Piguet Royal",
        "price": 250_000,
    },
    "gmt_master": {
        "name": "Rolex GMT-Master",
        "price": 500_000,
    },
    "patek_grand": {
        "name": "Patek Philippe Grand",
        "price": 1_000_000,
    },
    "rolex_olivia": {
        "name": "Rolex Olivia",
        "price": 5_000_000,
    },
}

BITCOIN_PRICE = 65_000
RESALE_RATE = 0.75


def money(value):
    value = float(value)

    if value.is_integer():
        return (
            f"{int(value):,}"
            .replace(
                ",",
                " "
            )
            + " €"
        )

    formatted = f"{value:,.2f}"

    formatted = (
        formatted
        .replace(",", " ")
        .replace(".", ",")
    )

    return formatted + " €"


def flex_embed(club, member):
    cars = club.get(
        "cars",
        []
    )

    watches = club.get(
        "watches",
        []
    )

    bitcoin = int(
        club.get(
            "bitcoin",
            0
        )
    )

    car_lines = []
    car_total = 0

    for item_id in cars:
        item = CARS.get(
            item_id,
            {
                "name": item_id,
                "price": 0
            }
        )

        car_total += int(
            item.get(
                "price",
                0
            )
        )

        car_lines.append(
            f"• **{item['name']}**\n"
            f"  *{money(item.get('price', 0))}*"
        )

    watch_lines = []
    watch_total = 0

    for item_id in watches:
        item = WATCHES.get(
            item_id,
            {
                "name": item_id,
                "price": 0
            }
        )

        watch_total += int(
            item.get(
                "price",
                0
            )
        )

        watch_lines.append(
            f"• **{item['name']}**\n"
            f"  *{money(item.get('price', 0))}*"
        )

    bitcoin_total = bitcoin * BITCOIN_PRICE

    collection_total = (
        car_total
        + watch_total
        + bitcoin_total
    )

    embed = discord.Embed(
        title=f"♣️ FLEX — {member.display_name}",
        description=(
            f"🏦 Boîte : **{club.get('name', 'Sans nom')}**\n"
            f"💶 Trésorerie : **{money(club.get('cash', 0))}**"
        ),
        color=0x101014
    )

    embed.add_field(
        name="₿ Bitcoin",
        value=(
            f"**{bitcoin} BTC**\n"
            f"*{money(BITCOIN_PRICE)} / BTC*\n"
            f"Valeur cumulée : **{money(bitcoin_total)}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🚘 Garage",
        value=(
            (
                "\n".join(
                    car_lines
                )
                + f"\n\nValeur cumulée : **{money(car_total)}**"
            )
            if car_lines
            else "Aucune voiture.\n\nValeur cumulée : **0 €**"
        )[:1024],
        inline=False
    )

    embed.add_field(
        name="⌚ Montres",
        value=(
            (
                "\n".join(
                    watch_lines
                )
                + f"\n\nValeur cumulée : **{money(watch_total)}**"
            )
            if watch_lines
            else "Aucune montre.\n\nValeur cumulée : **0 €**"
        )[:1024],
        inline=False
    )

    embed.add_field(
        name="💎 Valeur totale du FLEX",
        value=f"**{money(collection_total)}**",
        inline=False
    )

    embed.set_footer(
        text="♣️ Valeur affichée au prix d'achat boutique. Revente = 75 %."
    )

    return embed
