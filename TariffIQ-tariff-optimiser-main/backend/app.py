from flask import Flask, request, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Load suppliers
suppliers = pd.read_csv('./data/suppliers.csv')


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/suppliers', methods=['GET'])
def get_suppliers():
    """Return all suppliers"""
    return suppliers.to_dict(orient='records')


@app.route('/products', methods=['GET'])
def get_products():
    """Return unique product names"""
    return jsonify(sorted(suppliers["product"].str.strip().unique().tolist()))


@app.route('/countries', methods=['GET'])
def get_countries_for_product():
    """Return unique countries for a given product"""
    product = request.args.get('product')
    available_countries = suppliers[suppliers["product"].str.lower().str.strip() == product.lower().strip()]["country"].unique().tolist()
    return jsonify(available_countries)


@app.route('/impact', methods=['POST'])
def impact():
    """Calculate new cost after tariff"""
    data = request.json
    product = data.get('product')
    country = data.get('country')
    new_tariff = data.get('new_tariff')

    if not all([product, country, new_tariff is not None]):
        return jsonify({"error": "Missing required fields"}), 400

    matched_supplier = suppliers[
        (suppliers["product"].str.strip().str.lower() == product.strip().lower()) &
        (suppliers["country"].str.strip().str.lower() == country.strip().lower())
    ]

    if matched_supplier.empty:
        return jsonify({"impact": None, "error": "Product/Country not found"}), 404

    cost = matched_supplier["cost"].values[0]
    new_cost = cost + (cost * new_tariff / 100)

    return jsonify({"product": product, "country": country, "impact": new_cost})


@app.route('/add_supplier', methods=['POST'])
def add_supplier():
    """Add new supplier"""
    data = request.json
    global suppliers
    suppliers = pd.concat([suppliers, pd.DataFrame([data])], ignore_index=True)
    suppliers.to_csv('./data/suppliers.csv', index=False)  # Save to file
    return jsonify({"status": "success", "added": data})


@app.route("/debug_products", methods=["GET"])
def debug_products():
    """ Returns all available products in suppliers.csv """
    return jsonify(suppliers["product"].tolist())


@app.route("/optimize", methods=["POST"])
def optimize():
    """ Find the best cost supplier for a given product and country """
    data = request.json
    product = data.get("product")
    country = data.get("country")

    if not all([product, country]):
        return jsonify({"error": "Missing required fields (product, country)"}), 400

    filtered = suppliers[
        (suppliers["product"].str.strip().str.lower() == product.strip().lower()) &
        (suppliers["country"].str.strip().str.lower() == country.strip().lower())
    ]
    if filtered.empty:
        return jsonify({"error": "No suppliers found for this product and country."}), 404

    best_supplier = filtered.loc[filtered["cost"].idxmin()]
    results = []
    for _, row in filtered.iterrows():
        results.append({
            "name": row["name"],
            "cost": row["cost"],
            "difference": round(row["cost"] - best_supplier["cost"], 2),
            "difference_percent": round((row["cost"] - best_supplier["cost"]) / best_supplier["cost"] * 100, 2) if best_supplier["cost"] > 0 else 0
        })

    return jsonify({
        "product": product,
        "country": country,
        "best_supplier": best_supplier["name"],
        "results": results
    })


@app.route("/top_suppliers", methods=["GET"])
def top_suppliers():
    """ Returns the top suppliers ranked by average cost across products """
    grouped = suppliers.groupby(["name", "country"]).agg(
        avg_cost=("cost", "mean"),
        total_products=("product", "count")
    ).reset_index()
    top = grouped.sort_values(by="avg_cost").head(5).to_dict(orient="records")
    return jsonify(top)


if __name__ == '__main__':
    app.run(debug=True)
