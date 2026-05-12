/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// 1. Debrand Title Service
// Since the title service hardcodes "Odoo" as a fallback, 
// we ensure the 'odoo' part is always set to our brand.
const titleService = registry.category("services").get("title");
if (titleService) {
    const originalStart = titleService.start;
    titleService.start = function () {
        const result = originalStart.apply(this, arguments);
        const originalSetParts = result.setParts;
        result.setParts = function (parts) {
            if (parts && 'odoo' in parts) {
                parts.odoo = "ICS";
            }
            return originalSetParts.apply(this, arguments);
        };
        // Set initial brand
        result.setParts({ odoo: "ICS" });
        return result;
    };
}

// 2. Remove Odoo-specific items from User Menu
const userMenuRegistry = registry.category("user_menuitems");

// Odoo 19 IDs for these items
userMenuRegistry.remove("documentation");
userMenuRegistry.remove("support");
userMenuRegistry.remove("odoo_account");
userMenuRegistry.remove("shortcuts"); // Optional: remove if you want a cleaner menu

// 3. Debrand "About" dialog if possible (usually by patching the menu item)
// The "About" is often not in the registry but hardcoded or added differently.
// If it's in the registry, we can find its ID.
