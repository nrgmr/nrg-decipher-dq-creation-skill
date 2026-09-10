(function (global) {
    "use strict";

    var MIN_ROWS = 2;
    var LOG_NAME = "__DQ_NAME__";

    function textOf(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/<[^>]*>/g, "")
            .replace(/&nbsp;/g, " ")
            .replace(/&amp;/g, "&")
            .replace(/\s+/g, " ")
            .trim();
    }

    function Instance(boot) {
        this.params = boot.params || {};
        this.jsexport = boot.jsexport || {};
        this.isQa = !!boot.isQa;
        this.label = String(this.params.questionLabel || "");
        this.host = global.document.querySelector(
            '.__HOST_CLASS__[data-question-label="' + this.label + '"]');
        this.question = global.document.getElementById("question_" + this.label);
        this.rows = (this.jsexport.rows || []).slice(0);
        this.touchOrder = [];
        this.errors = [];
        this.cachedInputs = null;
    }

    Instance.prototype.captureInputs = function () {
        var name = this.params.captureOrder;
        var host;
        if (this.cachedInputs) { return this.cachedInputs; }
        if (!name || !global.jQuery) { return { length: 0 }; }
        host = global.jQuery("#question_" + name);
        this.cachedInputs = host.find("input.text-input");
        if (!this.cachedInputs.length) {
            this.cachedInputs = host.find('input[type="text"]');
        }
        return this.cachedInputs;
    };

    Instance.prototype.validateConfiguration = function () {
        if (!this.host) {
            this.errors.push("The host element for question " + this.label +
                " was not rendered.");
        }
        if (!this.question) {
            this.errors.push("Question " + this.label + " was not found on this" +
                " page.");
        }
        if (this.rows.length < MIN_ROWS) {
            this.errors.push("This question needs at least " + MIN_ROWS +
                " rows; it has " + this.rows.length + ".");
        }
        return this.errors.length === 0;
    };

    Instance.prototype.verifyCapture = function () {
        var inputs = this.captureInputs();
        var name = this.params.captureOrder;
        var original;
        var probe;
        if (!name) { return true; }
        if (!inputs.length) {
            this.errors.push("Capture variable " + name + " is not on this page." +
                " Is the capture block missing, or is there a suspend between it" +
                " and this question?");
            return false;
        }
        if (inputs.length < this.rows.length) {
            this.errors.push("Capture variable " + name + " has " +
                inputs.length + " row(s) but this question has " +
                this.rows.length + ".");
            return false;
        }
        original = inputs.eq(0).val();
        inputs.eq(0).val("1");
        probe = inputs.eq(0).val();
        inputs.eq(0).val(original);
        if (probe !== "1") {
            this.errors.push("Capture variable " + name + " is present but not" +
                " writable. A number field silently discards what the browser" +
                " writes; declare it as text.");
            return false;
        }
        return true;
    };

    Instance.prototype.build = function () {
        var self = this;
        var list = global.document.createElement("div");
        var markup = "";
        var index;

        for (index = 0; index < this.rows.length; index += 1) {
            markup += '<button type="button" class="card" data-row-index="' +
                index + '" aria-pressed="false">' +
                '<span class="card-text"></span>' +
                '<span class="card-mark" aria-hidden="true"></span>' +
                '</button>';
        }
        list.className = "card-list";
        list.innerHTML = markup;

        for (index = 0; index < this.rows.length; index += 1) {
            list.children[index].querySelector(".card-text").textContent =
                textOf(this.rows[index].text);
        }
        this.host.appendChild(list);

        this.host.addEventListener("click", function (event) {
            var card = event.target.closest ? event.target.closest(".card") : null;
            if (!card) { return; }
            event.preventDefault();
            self.select(card);
        }, false);

        this.host.addEventListener("keydown", function (event) {
            var target = event.target;
            if (event.key !== "Enter" && event.key !== " ") { return; }
            if (!target || !target.classList
                    || !target.classList.contains("card")) { return; }
            event.preventDefault();
            target.click();
        }, false);

        this.host.classList.add("is-ready");
    };

    Instance.prototype.select = function (card) {
        var index = parseInt(card.getAttribute("data-row-index"), 10);
        var row = this.rows[index];
        var cards;
        var native;
        var i;
        if (!row) { return; }

        if (this.touchOrder.indexOf(index) === -1) {
            this.touchOrder.push(index);
            this.writeOrder();
        }

        native = this.question
            ? this.question.querySelector('input[value="' + textOf(row.label) + '"]')
            : null;
        if (native) {
            native.checked = native.type === "checkbox" ? !native.checked : true;
            if (global.jQuery) {
                global.jQuery(native).trigger("change");
            }
        }

        cards = this.host.querySelectorAll(".card");
        for (i = 0; i < cards.length; i += 1) {
            cards[i].classList.toggle("is-selected", cards[i] === card);
            cards[i].setAttribute("aria-pressed",
                cards[i] === card ? "true" : "false");
        }
    };

    Instance.prototype.writeOrder = function () {
        var inputs = this.captureInputs();
        var index;
        var position;
        if (!inputs.length) { return; }
        for (index = 0; index < this.rows.length; index += 1) {
            position = this.touchOrder.indexOf(index);
            inputs.eq(index).val(position === -1 ? "" : String(position + 1));
        }
    };

    Instance.prototype.fail = function () {
        var box;
        var heading;
        var list;
        var index;
        var item;
        if (global.console && global.console.error) {
            global.console.error("[" + LOG_NAME + "/v" +
                String(this.params.version) + "] " + this.label + ": " +
                this.errors.join(" | "));
        }
        if (!this.host) { return; }
        this.host.innerHTML = "";
        box = global.document.createElement("div");
        box.className = "config-error";

        if (!this.isQa) {
            box.textContent = "This question is not available." +
                " Please contact the survey team.";
            this.host.appendChild(box);
            return;
        }

        heading = global.document.createElement("h3");
        heading.textContent = this.label + " is not configured correctly";
        box.appendChild(heading);
        list = global.document.createElement("ul");
        for (index = 0; index < this.errors.length; index += 1) {
            item = global.document.createElement("li");
            item.textContent = this.errors[index];
            list.appendChild(item);
        }
        box.appendChild(list);
        this.host.appendChild(box);
    };

    Instance.prototype.boot = function () {
        if (!this.validateConfiguration() || !this.verifyCapture()) {
            this.fail();
            return false;
        }
        this.build();
        this.writeOrder();
        return true;
    };

    function start() {
        var queue = global.__JS_NAMESPACE___BOOT || [];
        var registry = global.__JS_NAMESPACE___ || {};
        var index;
        var instance;
        for (index = 0; index < queue.length; index += 1) {
            instance = new Instance(queue[index]);
            if (registry[instance.label]) { continue; }
            registry[instance.label] = instance;
            instance.boot();
        }
        global.__JS_NAMESPACE___ = registry;
    }

    if (global.jQuery) {
        global.jQuery(global.document).ready(start);
    } else {
        global.document.addEventListener("DOMContentLoaded", start);
    }
}(window));
