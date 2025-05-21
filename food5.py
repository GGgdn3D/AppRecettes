# --- START OF FINAL CORRECTED FILE food.py ---

import requests
import xml.etree.ElementTree as ET
from flask import Flask, render_template_string, request, jsonify
from bs4 import BeautifulSoup
import sys
import traceback
import re # Import regex for cleaning text

# --- Configuration ---
SITEMAP_URLS = [
    "https://www.cuisineaz.com/xml/sitemap-cuisineaz-recette-1.xml",
    "https://www.cuisineaz.com/xml/sitemap-cuisineaz-recette-2.xml"
]
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Flask App Initialization ---
app = Flask(__name__)

# --- XML Parsing Logic (Sitemap) ---
# (Using the version from your provided file)
def fetch_and_parse_recipes(url):
    """Fetches a SINGLE XML sitemap and parses recipe URLs and images."""
    recipes = []
    error_message = None
    # print(f"Attempting to fetch sitemap: {url}") # Less verbose
    try:
        response = requests.get(url, headers=HEADERS, timeout=25)
        # print(f"Sitemap status code: {response.status_code}") # Less verbose
        response.raise_for_status()
        namespaces = {
            'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'image': 'http://www.google.com/schemas/sitemap-image/1.1'
        }
        xml_content = response.content
        root = ET.fromstring(xml_content)
        url_elements = root.findall('sitemap:url', namespaces)
        for url_element in url_elements:
            loc_element = url_element.find('sitemap:loc', namespaces)
            image_element = url_element.find('image:image', namespaces)
            image_loc_element = image_element.find('image:loc', namespaces) if image_element is not None else None
            recipe_url = loc_element.text if loc_element is not None else None
            image_url = image_loc_element.text if image_loc_element is not None else None
            if recipe_url:
                recipes.append({'url': recipe_url, 'image_url': image_url})
    except requests.exceptions.RequestException as e:
        error_message = f"Network error fetching sitemap {url.split('/')[-1]}: {e}"
        print(f"ERROR: {error_message}")
    except ET.ParseError as e:
        error_message = f"Error parsing XML sitemap {url.split('/')[-1]}. Error: {e}"
        print(f"ERROR: {error_message}")
    except Exception as e:
        error_message = f"Unexpected error processing sitemap {url.split('/')[-1]}: {e}"
        print(f"UNEXPECTED ERROR:")
        traceback.print_exc()
    return recipes, error_message


# --- Recipe Detail Scraping Logic (Ingredient Quantity Targeted) ---
def scrape_recipe_details(recipe_url):
    """Fetches and scrapes ingredients (name + quantity) and steps from a single recipe URL."""
    # Stores ingredients as list of dicts: [{'quantity': '...', 'name': '...'}, ...]
    details = {'ingredients': [], 'steps': []}
    error_message = None
    print(f"Attempting to scrape recipe details from: {recipe_url}")
    try:
        response = requests.get(recipe_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        print(f" -> Recipe page status code: {response.status_code}")
        soup = BeautifulSoup(response.content, 'lxml')

        # --- Find Ingredients (Targeting specific spans based on HTML snippet) ---
        details['ingredients'] = [] # Ensure list is empty before scraping
        ingredients_found = False
        print("--- Attempting Ingredient Extraction (Targeting Spans) ---")

        # Select the list items using the method assumed to work in your original file
        # Primarily target li.ingredient_item as shown in your snippet
        ingredient_list_items = soup.select('li.ingredient_item')
        # Add fallbacks similar to your original *if necessary*, but prioritize the specific selector
        if not ingredient_list_items:
             print("  -> 'li.ingredient_item' not found. Trying 'section.borderSection > li.ingredient'...")
             ingredients_section = soup.find('section', class_='borderSection')
             if ingredients_section:
                 ingredient_list_items = ingredients_section.find_all('li', class_='ingredient')
        # Add other fallbacks from your original working file if needed here

        print(f"  -> Found {len(ingredient_list_items)} potential ingredient list items.")

        if ingredient_list_items:
            for i, item in enumerate(ingredient_list_items):
                # 1. Find the NAME span specifically
                name_span = item.find('span', class_='ingredient_label')
                ingredient_name = name_span.get_text(strip=True) if name_span else None

                # 2. Find the QUANTITY span specifically
                # Use the exact class from your snippet
                quantity_span = item.find('span', class_='js-ingredient-qte ingredient_qte')
                quantity_text = quantity_span.get_text(strip=True) if quantity_span else ""

                # 3. Append ONLY if a valid name was found
                if ingredient_name:
                    details['ingredients'].append({
                        'quantity': quantity_text if quantity_text else "-", # Use "-" if quantity missing
                        'name': ingredient_name
                    })
                    ingredients_found = True
                    # print(f"    -> Added: Qty='{quantity_text if quantity_text else '-'}' Name='{ingredient_name}'") # Debug
                # else:
                    # print(f"    -> Warning: Skipping item {i+1}, couldn't find 'span.ingredient_label'.")

            if ingredients_found:
                 print(f"  -> Successfully parsed {len(details['ingredients'])} ingredients from list items.")
        else:
            print("  -> No ingredient list items found using primary selectors.")
            # If your original script had a global fallback like selecting labels directly, add it here.
            # Example:
            # print(" -> Trying direct selection of .ingredient_label as fallback...")
            # direct_labels = soup.select('.ingredient_label')
            # ... (add logic to append these with quantity '-') ...


        # --- Find Preparation Steps (Using Logic from your provided file) ---
        print("--- Attempting Step Extraction (Using Original Logic) ---")
        steps_found = False
        # Use the selectors confirmed to work from your original file
        preparation_list_ul = soup.find('ul', class_='preparation_steps')
        if preparation_list_ul:
            step_list_items = preparation_list_ul.find_all('li', class_='preparation_step', recursive=False) # Direct children
            if step_list_items:
                print(f"  -> Found {len(step_list_items)} preparation step list items (li.preparation_step).")
                for list_item in step_list_items:
                    step_paragraph = list_item.find('p') # Find 'p' inside the 'li'
                    if step_paragraph:
                        step_text = step_paragraph.get_text(strip=True)
                        if step_text:
                            details['steps'].append(step_text)
                            steps_found = True
                    # else: print(f"  -> Warning: No <p> tag found within this li.preparation_step.")
            # else: print(f"  -> Warning: Found ul.preparation_steps, but no li.preparation_step items within it.")
        # else: print(f"  -> Warning: Could not find the main preparation list (ul.preparation_steps).")

        # Fallback for steps ONLY if primary method found nothing (Keep your original fallback)
        if not steps_found:
            preparation_section = soup.find('section', id='preparation')
            if preparation_section:
                print(" -> Fallback: Trying any <p> tag inside section#preparation for steps.")
                fallback_paragraphs = preparation_section.find_all('p')
                count = 0
                seen_step_texts = set(details['steps']) # Avoid duplicates
                for p_tag in fallback_paragraphs:
                    step_text = p_tag.get_text(strip=True)
                    # Add a check to avoid adding short/irrelevant text or duplicates
                    if step_text and len(step_text) > 15 and step_text not in seen_step_texts:
                        details['steps'].append(step_text)
                        seen_step_texts.add(step_text)
                        steps_found = True
                        count += 1
                if count > 0:
                    print(f"  -> Added {count} steps via fallback.")
            # else: print(" -> Fallback section#preparation not found.")


        # --- Final Error/Warning Logic (from your file) ---
        if not details['ingredients']:
             print(f"Warning: Final ingredient list is empty for {recipe_url}.")
             error_message = error_message or "Could not find ingredients."
        if not details['steps']:
             print(f"Warning: Final preparation step list is empty for {recipe_url}.")
             error_message = error_message or "Could not find preparation steps."

        if not ingredients_found and not steps_found: # Updated condition
            error_message = "Could not find ingredients OR preparation steps."
            print(f"ERROR: {error_message} for {recipe_url}")

        print(f"Scraping finished for {recipe_url}. Found {len(details['ingredients'])} ingredients, {len(details['steps'])} steps.")

    except requests.exceptions.RequestException as e: error_message = f"Network error scraping: {e}"
    except Exception as e: error_message = f"Unexpected error scraping: {e}"; traceback.print_exc()
    if error_message and not details['ingredients'] and not details['steps']: print(f"ERROR during scraping: {error_message}")

    return details, error_message


# --- HTML Template (Ensuring Correct Display & JS Logic) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>20.000 Recipes</title>
    <style>
        /* --- Include ALL CSS from your previously working file --- */
        body { background-color: #1e1e1e; color: #e0e0e0; font-family: sans-serif; margin: 0; padding: 20px; overflow-x: hidden; }
        body.modal-open { overflow: hidden; }
        h1 { color: #eeeeee; text-align: center; border-bottom: 1px solid #444; padding-bottom: 10px; margin-bottom: 20px; }
        .search-container { margin-bottom: 25px; text-align: center; }
        #searchInput { padding: 10px 15px; width: 60%; max-width: 500px; border-radius: 20px; border: 1px solid #555; background-color: #333; color: #e0e0e0; font-size: 1em; outline: none; transition: border-color 0.2s, box-shadow 0.2s; }
        #searchInput:focus { border-color: #64b5f6; box-shadow: 0 0 5px rgba(100, 181, 246, 0.5); }
        #searchInput::placeholder { color: #888; }
        .recipe-list { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
        .recipe-item { background-color: #2a2a2a; border: 1px solid #444; border-radius: 8px; padding: 15px; text-align: center; transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden; min-height: 280px; cursor: pointer; }
        .recipe-item:hover { transform: translateY(-5px); box-shadow: 0 8px 15px rgba(0, 0, 0, 0.4); }
        .recipe-image-container { height: 180px; margin-bottom: 15px; display: flex; justify-content: center; align-items: center; background-color: #444; border-radius: 5px; overflow: hidden; pointer-events: none; flex-shrink: 0; }
        .recipe-item img { display: block; width: 100%; height: 100%; object-fit: cover; border-radius: 5px; pointer-events: none; }
        .recipe-item .image-unavailable, .recipe-item .no-image { color:#888; font-size: 0.9em; height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; pointer-events: none; text-align: center; padding: 5px; }
        .recipe-item span.recipe-title-link { color: #64b5f6; text-decoration: none; word-wrap: break-word; display: block; margin-top: auto; font-size: 1em; padding-top: 10px; pointer-events: none; font-weight: bold; line-height: 1.3; }
        .error { color: #ffbaba; background-color: #4d2020; padding: 15px; border: 1px solid #ff6b6b; border-radius: 5px; text-align: left; margin: 20px auto; max-width: 800px; }
        .error strong { color: #ff6b6b; display: block; margin-bottom: 10px; }
        .error ul { margin: 0; padding-left: 20px; }
        .error li { margin-bottom: 5px; }
        .no-recipes, #noResults { text-align: center; font-style: italic; color: #aaa; margin-top: 30px; padding: 20px; }
        #noResults { display: none; }
        /* --- Modal Styles --- */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.7); display: none; justify-content: center; align-items: center; z-index: 1000; opacity: 0; transition: opacity 0.3s ease-in-out; }
        .modal-overlay.active { display: flex; opacity: 1; }
        .modal-content { background-color: #2a2a2a; color: #e0e0e0; padding: 25px 30px; border-radius: 8px; border: 1px solid #444; width: 90%; max-width: 700px; max-height: 85vh; overflow-y: auto; position: relative; box-shadow: 0 5px 20px rgba(0, 0, 0, 0.5); transform: scale(0.95); transition: transform 0.3s ease-in-out; }
        .modal-overlay.active .modal-content { transform: scale(1); }
        .modal-close-btn { position: absolute; top: 10px; right: 15px; background: none; border: none; color: #aaa; font-size: 2.2rem; font-weight: bold; cursor: pointer; line-height: 1; padding: 0 5px; }
        .modal-close-btn:hover { color: #eee; }
        .modal-title { color: #eee; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid #444; padding-bottom: 10px; font-size: 1.4em; word-wrap: break-word; }
        .modal-title a { color: #7cc0f5; text-decoration: none; }
        .modal-title a:hover { text-decoration: underline; }
        .modal-section-title { color: #ccc; font-size: 1.2em; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px dashed #444; padding-bottom: 5px; }
        .modal-ingredients-list, .modal-steps-list { padding-left: 5px; margin-bottom: 20px; line-height: 1.6; font-size: 0.95em; }
        /* Style for Quantity display */
        .modal-ingredients-list { list-style-type: none; }
        .modal-ingredients-list li { margin-bottom: 8px; }
        .modal-ingredients-list .quantity { font-weight: bold; color: #ddd; display: inline-block; min-width: 60px; margin-right: 10px; text-align: right; }
        /* Style for Steps */
        .modal-steps-list { list-style-type: decimal; padding-left: 25px; }
        .modal-steps-list li { margin-bottom: 8px; }
        .modal-loading, .modal-error { text-align: center; padding: 40px 10px; font-size: 1.1em; color: #aaa; }
        .modal-error { color: #ff8a8a; }
    </style>
</head>
<body>
    <h1> Recipes Sitemap</h1>

    <!-- Sitemap Loading Errors -->
    {% if errors %}
    <div class="error">
        <strong>Encountered issues loading sitemaps:</strong>
        <ul>{% for e in errors %}<li>{{ e }}</li>{% endfor %}</ul>
    </div>
    {% endif %}

    <!-- Search Input -->
    <div class="search-container">
        <form onsubmit="return false;">
            <input type="search" id="searchInput" placeholder="Search recipes by name..." oninput="filterRecipes()">
            <p> A chaque fois les quantité sont  pour 6 personnes </p>
        </form>
    </div>

    <!-- Recipe List -->
    {% if recipes %}
        <ul class="recipe-list" id="recipeList">
            {% for recipe in recipes %}
                <li class="recipe-item" data-url="{{ recipe.url }}">
                    <div class="recipe-image-container">
                    {% if recipe.image_url %}
                        <img src="{{ recipe.image_url }}" alt="Image for {{ recipe.url.split('/')[-1].replace('.aspx', '') | title }}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" loading="lazy">
                        <div class="image-unavailable" style="display:none;">(Image unavailable)</div>
                    {% else %}
                         <div class="no-image">(No image provided)</div>
                    {% endif %}
                    </div>
                    {% if recipe.url %}
                    <span class="recipe-title-link">
                        {{ recipe.url.split('/')[-1].replace('.aspx', '').replace('-', ' ') | title }}
                    </span>
                    {% else %}
                     <span class="recipe-title-link">(Invalid recipe data)</span>
                    {% endif %}
                </li>
            {% endfor %}
        </ul>
        <p id="noResults">No matching recipes found.</p>
        <p style="text-align:center; color: #777; margin-top: 20px; font-size: 0.8em;">Displaying {{ recipes | length }} total recipes.</p>
    {% elif not errors %}
        <p class="no-recipes">No recipes found in the specified sitemaps.</p>
    {% endif %}

    <!-- Modal Structure -->
    <div class="modal-overlay" id="recipeModalOverlay">
        <div class="modal-content" id="recipeModalContent">
             <button class="modal-close-btn" id="modalCloseBtn" aria-label="Close modal">&times;</button>
            <h2 class="modal-title" id="modalRecipeTitle">Recipe Title</h2>
            <div id="modalBody">
                 <div class="modal-loading" id="modalLoadingIndicator">Loading...</div>
                 <div class="modal-error" id="modalErrorMsg" style="display: none;"></div>
                 <div id="modalRecipeData" style="display: none;">
                     <h3 class="modal-section-title">Ingredients</h3>
                     <ul class="modal-ingredients-list" id="modalIngredientsList"></ul>
                     <h3 class="modal-section-title">Preparation Steps</h3>
                     <ol class="modal-steps-list" id="modalStepsList"></ol>
                 </div>
            </div>
        </div>
    </div>

    <!-- JavaScript (Ingredient Display Updated) -->
    <script>
        // --- Search Filter Function ---
        function filterRecipes() {
            const searchInput = document.getElementById('searchInput');
            if (!searchInput) return;
            const filter = searchInput.value.toLowerCase();
            const recipeList = document.getElementById('recipeList');
            if (!recipeList) return;
            const items = recipeList.getElementsByClassName('recipe-item');
            const noResultsMsg = document.getElementById('noResults');
            let visibleCount = 0;
            for (let i = 0; i < items.length; i++) {
                const titleElement = items[i].querySelector('.recipe-title-link');
                const txtValue = titleElement ? (titleElement.textContent || titleElement.innerText) : '';
                if (txtValue.toLowerCase().includes(filter)) {
                    items[i].style.display = "flex"; visibleCount++;
                } else { items[i].style.display = "none"; }
            }
            noResultsMsg.style.display = (visibleCount === 0 && filter !== '') ? 'block' : 'none';
        }
        // Initial call moved to DOMContentLoaded

        // --- Modal Handling Variables ---
        const modalOverlay = document.getElementById('recipeModalOverlay');
        const modalContent = document.getElementById('recipeModalContent');
        const modalCloseBtn = document.getElementById('modalCloseBtn');
        const modalRecipeTitle = document.getElementById('modalRecipeTitle');
        const modalLoadingIndicator = document.getElementById('modalLoadingIndicator');
        const modalErrorMsg = document.getElementById('modalErrorMsg');
        const modalRecipeData = document.getElementById('modalRecipeData');
        const modalIngredientsList = document.getElementById('modalIngredientsList');
        const modalStepsList = document.getElementById('modalStepsList');

        // --- Modal Functions (show/hide) ---
        function showModal() { document.body.classList.add('modal-open'); modalOverlay.classList.add('active'); }
        function hideModal() { document.body.classList.remove('modal-open'); modalOverlay.classList.remove('active'); setTimeout(() => { modalLoadingIndicator.style.display = 'block'; modalErrorMsg.style.display = 'none'; modalRecipeData.style.display = 'none'; modalIngredientsList.innerHTML = ''; modalStepsList.innerHTML = ''; modalRecipeTitle.innerHTML = 'Recipe Details'; }, 300); }

        // --- Event Listeners Setup ---
        document.addEventListener('DOMContentLoaded', () => {
            const recipeListElement = document.getElementById('recipeList');
            const searchInput = document.getElementById('searchInput');

            if (searchInput) { filterRecipes(); } // Initial filter call
            else { console.error("Search input 'searchInput' not found."); }

            if (recipeListElement) {
                console.log("Recipe list found, attaching click listener.");
                recipeListElement.addEventListener('click', (event) => {
                    const clickedItem = event.target.closest('.recipe-item');
                    if (clickedItem) {
                        const recipeUrl = clickedItem.dataset.url;
                        const titleSpan = clickedItem.querySelector('.recipe-title-link');
                        const recipeTitleText = titleSpan ? titleSpan.textContent.trim() : 'Recipe';

                        if (recipeUrl) {
                            modalRecipeTitle.innerHTML = `<a href="${recipeUrl}" target="_blank" rel="noopener noreferrer">${recipeTitleText}</a>`;
                            modalLoadingIndicator.style.display = 'block'; modalErrorMsg.style.display = 'none'; modalRecipeData.style.display = 'none';
                            showModal();

                            fetch(`/get_recipe_details?url=${encodeURIComponent(recipeUrl)}`)
                                .then(response => { if (!response.ok) { throw new Error(`HTTP ${response.status}: ${response.statusText}`); } return response.json(); })
                                .then(data => {
                                    console.log("Received recipe details:", data); // Log received data
                                    modalLoadingIndicator.style.display = 'none';
                                    if (data.success) {
                                        // --- CORRECTED Ingredient Display ---
                                        modalIngredientsList.innerHTML = '';
                                        if (data.details.ingredients && data.details.ingredients.length > 0) {
                                            data.details.ingredients.forEach(ing => {
                                                const li = document.createElement('li');
                                                const quantitySpan = document.createElement('span');
                                                quantitySpan.className = 'quantity';
                                                quantitySpan.textContent = ing.quantity || "-"; // Use data field

                                                const nameText = document.createTextNode(ing.name ? (' ' + ing.name) : ' (name missing)'); // Use data field

                                                li.appendChild(quantitySpan);
                                                li.appendChild(nameText);
                                                modalIngredientsList.appendChild(li);
                                            });
                                        } else { modalIngredientsList.innerHTML = '<li>Could not find ingredients details.</li>'; }

                                        // --- Step display logic (Unchanged) ---
                                        modalStepsList.innerHTML = '';
                                        if (data.details.steps && data.details.steps.length > 0) {
                                            data.details.steps.forEach(step => { const li = document.createElement('li'); li.textContent = step; modalStepsList.appendChild(li); });
                                         } else { modalStepsList.innerHTML = '<li>Could not find preparation step details.</li>'; }

                                        if(data.warning) { console.warn("Scraping Warning:", data.warning); }
                                        modalRecipeData.style.display = 'block';
                                    } else {
                                        modalErrorMsg.textContent = `Error: ${data.error || 'Could not load recipe data.'}`;
                                        modalErrorMsg.style.display = 'block';
                                    }
                                })
                                .catch(error => {
                                    console.error('Fetch Error:', error);
                                    modalLoadingIndicator.style.display = 'none';
                                    modalErrorMsg.textContent = `Failed to fetch details. ${error.message}.`;
                                    modalErrorMsg.style.display = 'block';
                                });
                        } else { console.error("Clicked item missing data-url attribute."); }
                    }
                });
            } else { console.error("CRITICAL ERROR: Recipe list element with ID 'recipeList' not found."); }

            if (modalCloseBtn) { modalCloseBtn.addEventListener('click', hideModal); }
            else { console.error("Modal close button not found."); }

            if (modalOverlay) { modalOverlay.addEventListener('click', (event) => { if (event.target === modalOverlay) { hideModal(); } }); }
            else { console.error("Modal overlay not found."); }

            document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && modalOverlay && modalOverlay.classList.contains('active')) { hideModal(); } });

        }); // End DOMContentLoaded
    </script>
</body>
</html>
"""

# --- Flask Routes (Keep as is from your file) ---
@app.route('/')
def index():
    all_recipes = []
    fetch_errors = []
    for url in SITEMAP_URLS:
        recipes_data, error_data = fetch_and_parse_recipes(url)
        if recipes_data: all_recipes.extend(recipes_data)
        if error_data: fetch_errors.append(error_data)
    unique_recipes = []
    seen_urls = set()
    for recipe in all_recipes:
        if recipe.get('url') and recipe['url'] not in seen_urls:
            unique_recipes.append(recipe)
            seen_urls.add(recipe['url'])
    print(f"--- Displaying {len(unique_recipes)} unique recipes. Sitemap errors: {len(fetch_errors)} ---")
    return render_template_string(HTML_TEMPLATE, recipes=unique_recipes, errors=fetch_errors)

@app.route('/get_recipe_details')
def get_recipe_details():
    recipe_url = request.args.get('url')
    if not recipe_url: return jsonify(success=False, error="Missing 'url' parameter"), 400
    if not recipe_url.startswith(('http://', 'https://')): return jsonify(success=False, error="Invalid URL format"), 400
    details, error_msg = scrape_recipe_details(recipe_url) # Call the modified scraper
    if error_msg and not details['ingredients'] and not details['steps']: return jsonify(success=False, error=error_msg)
    elif error_msg: return jsonify(success=True, details=details, warning=error_msg)
    else: return jsonify(success=True, details=details)

# --- Run the App (Keep as is from your file) ---
if __name__ == '__main__':
    try: import bs4; import lxml
    except ImportError: print("Error: Install beautifulsoup4 and lxml"); sys.exit(1)
    if sys.version_info[0] < 3: print("Warning: Requires Python 3."); sys.exit(1)
    print(f"Starting Flask server. View at http://127.0.0.1:5200")
    app.run(port=5200, debug=True) # Use debug=True for development

# --- END OF FINAL CORRECTED FILE food.py ---