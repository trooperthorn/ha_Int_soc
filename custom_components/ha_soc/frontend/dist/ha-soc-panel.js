function e(e,t,s,i){var r,n=arguments.length,o=n<3?t:null===i?i=Object.getOwnPropertyDescriptor(t,s):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)o=Reflect.decorate(e,t,s,i);else for(var a=e.length-1;a>=0;a--)(r=e[a])&&(o=(n<3?r(o):n>3?r(t,s,o):r(t,s))||o);return n>3&&o&&Object.defineProperty(t,s,o),o}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,s=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),r=new WeakMap;let n=class{constructor(e,t,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(s&&void 0===e){const s=void 0!==t&&1===t.length;s&&(e=r.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),s&&r.set(t,e))}return e}toString(){return this.cssText}};const o=e=>new n("string"==typeof e?e:e+"",void 0,i),a=(e,...t)=>{const s=1===e.length?e[0]:t.reduce((t,s,i)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+e[i+1],e[0]);return new n(s,e,i)},l=s?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const s of e.cssRules)t+=s.cssText;return o(t)})(e):e,{is:h,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:u,getOwnPropertySymbols:p,getPrototypeOf:_}=Object,f=globalThis,g=f.trustedTypes,v=g?g.emptyScript:"",m=f.reactiveElementPolyfillSupport,y=(e,t)=>e,b={toAttribute(e,t){switch(t){case Boolean:e=e?v:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let s=e;switch(t){case Boolean:s=null!==e;break;case Number:s=null===e?null:Number(e);break;case Object:case Array:try{s=JSON.parse(e)}catch(e){s=null}}return s}},w=(e,t)=>!h(e,t),S={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:w};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),f.litPropertyMetadata??=new WeakMap;let x=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=S){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(e,s,t);void 0!==i&&c(this.prototype,e,i)}}static getPropertyDescriptor(e,t,s){const{get:i,set:r}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:i,set(t){const n=i?.call(this);r?.call(this,t),this.requestUpdate(e,n,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??S}static _$Ei(){if(this.hasOwnProperty(y("elementProperties")))return;const e=_(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(y("properties"))){const e=this.properties,t=[...u(e),...p(e)];for(const s of t)this.createProperty(s,e[s])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,s]of t)this.elementProperties.set(e,s)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const s=this._$Eu(e,t);void 0!==s&&this._$Eh.set(s,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const s=new Set(e.flat(1/0).reverse());for(const e of s)t.unshift(l(e))}else void 0!==e&&t.push(l(e));return t}static _$Eu(e,t){const s=t.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const s of t.keys())this.hasOwnProperty(s)&&(e.set(s,this[s]),delete this[s]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,i)=>{if(s)e.adoptedStyleSheets=i.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const s of i){const i=document.createElement("style"),r=t.litNonce;void 0!==r&&i.setAttribute("nonce",r),i.textContent=s.cssText,e.appendChild(i)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,s){this._$AK(e,s)}_$ET(e,t){const s=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,s);if(void 0!==i&&!0===s.reflect){const r=(void 0!==s.converter?.toAttribute?s.converter:b).toAttribute(t,s.type);this._$Em=e,null==r?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(e,t){const s=this.constructor,i=s._$Eh.get(e);if(void 0!==i&&this._$Em!==i){const e=s.getPropertyOptions(i),r="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:b;this._$Em=i;const n=r.fromAttribute(t,e.type);this[i]=n??this._$Ej?.get(i)??n,this._$Em=null}}requestUpdate(e,t,s,i=!1,r){if(void 0!==e){const n=this.constructor;if(!1===i&&(r=this[e]),s??=n.getPropertyOptions(e),!((s.hasChanged??w)(r,t)||s.useDefault&&s.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(n._$Eu(e,s))))return;this.C(e,t,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:s,reflect:i,wrapped:r},n){s&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,n??t??this[e]),!0!==r||void 0!==n)||(this._$AL.has(e)||(this.hasUpdated||s||(t=void 0),this._$AL.set(e,t)),!0===i&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,s]of e){const{wrapped:e}=s,i=this[t];!0!==e||this._$AL.has(t)||void 0===i||this.C(t,void 0,s,i)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[y("elementProperties")]=new Map,x[y("finalized")]=new Map,m?.({ReactiveElement:x}),(f.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const $=globalThis,k=e=>e,C=$.trustedTypes,E=C?C.createPolicy("lit-html",{createHTML:e=>e}):void 0,R="$lit$",P=`lit$${Math.random().toFixed(9).slice(2)}$`,A="?"+P,T=`<${A}>`,D=document,L=()=>D.createComment(""),M=e=>null===e||"object"!=typeof e&&"function"!=typeof e,B=Array.isArray,O="[ \t\n\f\r]",z=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,I=/-->/g,N=/>/g,F=RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),H=/'/g,W=/"/g,U=/^(?:script|style|textarea|title)$/i,K=(e=>(t,...s)=>({_$litType$:e,strings:t,values:s}))(1),V=Symbol.for("lit-noChange"),j=Symbol.for("lit-nothing"),q=new WeakMap,Y=D.createTreeWalker(D,129);function G(e,t){if(!B(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==E?E.createHTML(t):t}let X=class e{constructor({strings:t,_$litType$:s},i){let r;this.parts=[];let n=0,o=0;const a=t.length-1,l=this.parts,[h,c]=((e,t)=>{const s=e.length-1,i=[];let r,n=2===t?"<svg>":3===t?"<math>":"",o=z;for(let t=0;t<s;t++){const s=e[t];let a,l,h=-1,c=0;for(;c<s.length&&(o.lastIndex=c,l=o.exec(s),null!==l);)c=o.lastIndex,o===z?"!--"===l[1]?o=I:void 0!==l[1]?o=N:void 0!==l[2]?(U.test(l[2])&&(r=RegExp("</"+l[2],"g")),o=F):void 0!==l[3]&&(o=F):o===F?">"===l[0]?(o=r??z,h=-1):void 0===l[1]?h=-2:(h=o.lastIndex-l[2].length,a=l[1],o=void 0===l[3]?F:'"'===l[3]?W:H):o===W||o===H?o=F:o===I||o===N?o=z:(o=F,r=void 0);const d=o===F&&e[t+1].startsWith("/>")?" ":"";n+=o===z?s+T:h>=0?(i.push(a),s.slice(0,h)+R+s.slice(h)+P+d):s+P+(-2===h?t:d)}return[G(e,n+(e[s]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),i]})(t,s);if(this.el=e.createElement(h,i),Y.currentNode=this.el.content,2===s||3===s){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(r=Y.nextNode())&&l.length<a;){if(1===r.nodeType){if(r.hasAttributes())for(const e of r.getAttributeNames())if(e.endsWith(R)){const t=c[o++],s=r.getAttribute(e).split(P),i=/([.?@])?(.*)/.exec(t);l.push({type:1,index:n,name:i[2],strings:s,ctor:"."===i[1]?te:"?"===i[1]?se:"@"===i[1]?ie:ee}),r.removeAttribute(e)}else e.startsWith(P)&&(l.push({type:6,index:n}),r.removeAttribute(e));if(U.test(r.tagName)){const e=r.textContent.split(P),t=e.length-1;if(t>0){r.textContent=C?C.emptyScript:"";for(let s=0;s<t;s++)r.append(e[s],L()),Y.nextNode(),l.push({type:2,index:++n});r.append(e[t],L())}}}else if(8===r.nodeType)if(r.data===A)l.push({type:2,index:n});else{let e=-1;for(;-1!==(e=r.data.indexOf(P,e+1));)l.push({type:7,index:n}),e+=P.length-1}n++}}static createElement(e,t){const s=D.createElement("template");return s.innerHTML=e,s}};function J(e,t,s=e,i){if(t===V)return t;let r=void 0!==i?s._$Co?.[i]:s._$Cl;const n=M(t)?void 0:t._$litDirective$;return r?.constructor!==n&&(r?._$AO?.(!1),void 0===n?r=void 0:(r=new n(e),r._$AT(e,s,i)),void 0!==i?(s._$Co??=[])[i]=r:s._$Cl=r),void 0!==r&&(t=J(e,r._$AS(e,t.values),r,i)),t}class Z{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:s}=this._$AD,i=(e?.creationScope??D).importNode(t,!0);Y.currentNode=i;let r=Y.nextNode(),n=0,o=0,a=s[0];for(;void 0!==a;){if(n===a.index){let t;2===a.type?t=new Q(r,r.nextSibling,this,e):1===a.type?t=new a.ctor(r,a.name,a.strings,this,e):6===a.type&&(t=new re(r,this,e)),this._$AV.push(t),a=s[++o]}n!==a?.index&&(r=Y.nextNode(),n++)}return Y.currentNode=D,i}p(e){let t=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(e,s,t),t+=s.strings.length-2):s._$AI(e[t])),t++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,s,i){this.type=2,this._$AH=j,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=J(this,e,t),M(e)?e===j||null==e||""===e?(this._$AH!==j&&this._$AR(),this._$AH=j):e!==this._$AH&&e!==V&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>B(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==j&&M(this._$AH)?this._$AA.nextSibling.data=e:this.T(D.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:s}=e,i="number"==typeof s?this._$AC(e):(void 0===s.el&&(s.el=X.createElement(G(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(t);else{const e=new Z(i,this),s=e.u(this.options);e.p(t),this.T(s),this._$AH=e}}_$AC(e){let t=q.get(e.strings);return void 0===t&&q.set(e.strings,t=new X(e)),t}k(e){B(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let s,i=0;for(const r of e)i===t.length?t.push(s=new Q(this.O(L()),this.O(L()),this,this.options)):s=t[i],s._$AI(r),i++;i<t.length&&(this._$AR(s&&s._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}let ee=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,s,i,r){this.type=1,this._$AH=j,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=r,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=j}_$AI(e,t=this,s,i){const r=this.strings;let n=!1;if(void 0===r)e=J(this,e,t,0),n=!M(e)||e!==this._$AH&&e!==V,n&&(this._$AH=e);else{const i=e;let o,a;for(e=r[0],o=0;o<r.length-1;o++)a=J(this,i[s+o],t,o),a===V&&(a=this._$AH[o]),n||=!M(a)||a!==this._$AH[o],a===j?e=j:e!==j&&(e+=(a??"")+r[o+1]),this._$AH[o]=a}n&&!i&&this.j(e)}j(e){e===j?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}};class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===j?void 0:e}}let se=class extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==j)}},ie=class extends ee{constructor(e,t,s,i,r){super(e,t,s,i,r),this.type=5}_$AI(e,t=this){if((e=J(this,e,t,0)??j)===V)return;const s=this._$AH,i=e===j&&s!==j||e.capture!==s.capture||e.once!==s.once||e.passive!==s.passive,r=e!==j&&(s===j||i);i&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}};class re{constructor(e,t,s){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(e){J(this,e)}}const ne=$.litHtmlPolyfillSupport;ne?.(X,Q),($.litHtmlVersions??=[]).push("3.3.3");const oe=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class ae extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,s)=>{const i=s?.renderBefore??t;let r=i._$litPart$;if(void 0===r){const e=s?.renderBefore??null;i._$litPart$=r=new Q(t.insertBefore(L(),e),e,void 0,s??{})}return r._$AI(e),r})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return V}}ae._$litElement$=!0,ae.finalized=!0,oe.litElementHydrateSupport?.({LitElement:ae});const le=oe.litElementPolyfillSupport;le?.({LitElement:ae}),(oe.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const he=e=>(t,s)=>{void 0!==s?s.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},ce={attribute:!0,type:String,converter:b,reflect:!1,hasChanged:w},de=(e=ce,t,s)=>{const{kind:i,metadata:r}=s;let n=globalThis.litPropertyMetadata.get(r);if(void 0===n&&globalThis.litPropertyMetadata.set(r,n=new Map),"setter"===i&&((e=Object.create(e)).wrapped=!0),n.set(s.name,e),"accessor"===i){const{name:i}=s;return{set(s){const r=t.get.call(this);t.set.call(this,s),this.requestUpdate(i,r,e,!0,s)},init(t){return void 0!==t&&this.C(i,void 0,e,t),t}}}if("setter"===i){const{name:i}=s;return function(s){const r=this[i];t.call(this,s),this.requestUpdate(i,r,e,!0,s)}}throw Error("Unsupported decorator location: "+i)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ue(e){return(t,s)=>"object"==typeof s?de(e,t,s):((e,t,s)=>{const i=t.hasOwnProperty(s);return t.constructor.createProperty(s,e),i?Object.getOwnPropertyDescriptor(t,s):void 0})(e,t,s)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pe(e){return ue({...e,state:!0,attribute:!1})}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const _e=[{id:"overview",label:"Overview",defaultTab:"dashboard",tabs:[{id:"dashboard",label:"Security Overview"}]},{id:"assets",label:"Assets",defaultTab:"network",tabs:[{id:"network",label:"Network"},{id:"peripherals",label:"Local Peripherals"},{id:"entity_remap",label:"Entity ReMap"},{id:"entity_map",label:"Entity Map"},{id:"dashboard_files",label:"Dashboard Files"},{id:"integration_security",label:"Integration Security"}]},{id:"findings",label:"Findings",defaultTab:"scanner",tabs:[{id:"scanner",label:"Vulnerability Scanner"},{id:"network_security",label:"Network Security"}]},{id:"identity",label:"Identity",defaultTab:"users",tabs:[{id:"users",label:"Users & Access"},{id:"permissions",label:"Permissions"}]},{id:"siem",label:"SIEM & Audit",defaultTab:"audit",tabs:[{id:"audit",label:"Audit Log"},{id:"logs",label:"Logs"}]},{id:"terminal",label:"Terminal",defaultTab:"terminal",tabs:[{id:"terminal",label:"Terminal"}]},{id:"settings",label:"Settings",defaultTab:"settings",ownerOnly:!0,tabs:[{id:"settings",label:"Security Settings"}]}];function fe(e,t,s){e.dispatchEvent(new CustomEvent("ha-soc-navigate",{detail:s?{tab:t,clientFilter:s}:{tab:t},bubbles:!0,composed:!0}))}function ge(e){window.history.pushState(null,"",e),window.dispatchEvent(new CustomEvent("location-changed",{bubbles:!0,composed:!0}))}function ve(e){return`/config/devices/dashboard?historyBack=1&config_entry=${e}`}const me=[["any",null,null],["echo-request",8,128],["echo-reply",0,129],["destination-unreachable",3,1],["time-exceeded",11,3],["parameter-problem",12,4],["packet-too-big",null,2],["router-solicitation",null,133],["router-advertisement",null,134],["neighbour-solicitation",null,135],["neighbour-advertisement",null,136]],ye=(e,t,s)=>we(e,{type:"ha_soc/crash_forensics/bundle",id:t,file:s}).then(e=>e.content),be=["host-journal-prev-boot.txt","kernel.txt","supervisor.txt","core.txt","host-info.json","resolution-info.json","supervisor-info.json","os-info.json","containers.json","fault-log.txt","watchdog-history.json","summary.json"],we=(e,t)=>e.callWS(t),Se=e=>we(e,{type:"ha_soc/users/list"}).then(e=>e.users),xe=e=>we(e,{type:"ha_soc/risk/list"}).then(e=>e.risk),$e=(e,t)=>we(e,{type:"ha_soc/detections/list",status:t}).then(e=>e.detections),ke=(e,t,s)=>we(e,{type:"ha_soc/detections/set_status",detection_id:t,status:s}),Ce=e=>we(e,{type:"ha_soc/detections/thresholds"}).then(e=>e.rules),Ee=e=>we(e,{type:"ha_soc/vulns/list"}).then(e=>e.findings),Re=e=>we(e,{type:"ha_soc/logs/fault"}),Pe=e=>we(e,{type:"ha_soc/logs/targets"}),Ae=e=>we(e,{type:"ha_soc/logs/boots"}),Te=e=>we(e,{type:"ha_soc/health/list"}),De=e=>we(e,{type:"ha_soc/dashboard/devices"}),Le=e=>we(e,{type:"ha_soc/dashboard/integrations"}),Me=e=>we(e,{type:"ha_soc/access/info"}),Be=e=>we(e,{type:"ha_soc/probe/status"}),Oe=e=>we(e,{type:"ha_soc/firewall/status"}),ze=e=>we(e,{type:"ha_soc/netscan/status"}),Ie=e=>we(e,{type:"ha_soc/peripherals/list"}),Ne=e=>we(e,{type:"ha_soc/entity_remap/broken_references"}).then(e=>e.broken),Fe=e=>we(e,{type:"ha_soc/security_health/list"}),He=e=>we(e,{type:"ha_soc/network/overview"}),We=(e,t)=>we(e,{type:"ha_soc/settings/set",...t}),Ue=e=>we(e,{type:"ha_soc/unifi_ledger/get"}),Ke=e=>we(e,{type:"ha_soc/ssh/status"}),Ve=(e,t)=>we(e,{type:"ha_soc/terminal/close",session_id:t}),je=(e,t,s,i,r,n)=>we(e,{type:"ha_soc/terminal/export_event",kind:t,...n?{session_id:n}:{},lines:s,bytes:i,sha256:r}),qe=a`
  :host {
    display: block;
    padding: 20px clamp(14px, 2vw, 24px) 28px;
    max-width: 1400px;
    margin: 0 auto;
    container-type: inline-size;

    /* HA SOC semantic surface tokens.  They inherit the active Home
       Assistant theme, but give this panel one stable vocabulary for its
       reference layout and visual-regression fixtures. */
    --soc-page-bg: var(--primary-background-color);
    --soc-surface: var(--card-background-color, #fff);
    --soc-surface-subtle: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.035);
    --soc-border: var(--divider-color);
    --soc-text: var(--primary-text-color);
    --soc-text-muted: var(--secondary-text-color);
    --soc-accent: var(--primary-color);
    --soc-card-radius: var(--ha-card-border-radius, 12px);

    /* Validated categorical palette (dataviz skill reference instance) —
       adjacent-pair CVD/contrast checked for chart use (bars, lines,
       stacks). Light values here; .dark overrides the dark-mode steps. */
    --cat-1: #2a78d6;
    --cat-2: #eb6834;
    --cat-3: #1baf7a;
    --cat-4: #eda100;
    --cat-5: #e87ba4;
    --cat-6: #008300;
    --cat-7: #4a3aa7;
    --cat-8: #e34948;
    --cat-other: #9aa0a6;

    /* Reserved status roles — never reused as a plain series color. */
    --status-good: #0ca30c;
    --status-warning: #fab219;
    --status-serious: #ec835a;
    --status-critical: #d03b3b;
  }
  :host(.dark) {
    --cat-1: #3987e5;
    --cat-2: #d95926;
    --cat-3: #199e70;
    --cat-4: #c98500;
    --cat-5: #d55181;
    --cat-6: #008300;
    --cat-7: #9085e9;
    --cat-8: #e66767;
    --cat-other: #7a807f;
  }
  .tabs {
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--divider-color);
    margin-bottom: 16px;
    overflow-x: auto;
  }
  .tab {
    padding: 12px 16px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--secondary-text-color);
    border-bottom: 2px solid transparent;
    white-space: nowrap;
  }
  .tab.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }
  .card {
    background: var(--soc-surface);
    border-radius: var(--soc-card-radius);
    border: 1px solid var(--soc-border);
    box-shadow: none;
    padding: 16px;
    margin-bottom: 16px;
  }
  .card h3 {
    margin: 0 0 12px;
    font-size: 15px;
    font-weight: 650;
    letter-spacing: -0.005em;
    color: var(--primary-text-color);
  }
  /* Two-column responsive grid for the Settings tab's cards; collapses to
     one column under 700px of the panel's own inline size (:host has
     container-type: inline-size). */
  .settings-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
    align-items: start;
  }
  @container (max-width: 700px) {
    .settings-grid {
      grid-template-columns: 1fr;
    }
  }
  /* Collapsible cards: native <details class="card"> with the h3 (and an
     optional status pill) moved into <summary>. */
  details.card {
    padding: 0;
    margin-bottom: 0;
  }
  details.card > summary.card-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    list-style: none;
    cursor: pointer;
    padding: 16px;
    user-select: none;
  }
  details.card > summary.card-summary::-webkit-details-marker {
    display: none;
  }
  details.card > summary.card-summary::before {
    content: "▸";
    display: inline-block;
    margin-right: 8px;
    font-size: 11px;
    color: var(--secondary-text-color);
    transition: transform 0.15s ease;
  }
  details.card[open] > summary.card-summary::before {
    transform: rotate(90deg);
  }
  details.card > summary.card-summary h3 {
    margin: 0;
    flex: 1;
  }
  details.card > *:not(summary) {
    padding: 0 16px;
  }
  details.card > *:last-child {
    padding-bottom: 16px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th,
  td {
    text-align: left;
    padding: 8px 10px;
    border-bottom: 1px solid var(--divider-color);
    vertical-align: top;
  }
  th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--secondary-text-color);
  }
  tr:hover td {
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.03);
  }
  tr.row-disabled td {
    background: rgba(var(--rgb-error-color, 219, 68, 55), 0.05);
    color: var(--secondary-text-color);
  }
  tr.row-disabled td:first-child > div:first-child {
    text-decoration: line-through;
    text-decoration-color: var(--secondary-text-color);
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 100px;
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
  }
  .pill .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }
  .pill.critical .dot,
  .pill.high .dot {
    background: var(--error-color, #db4437);
  }
  .pill.medium .dot {
    background: var(--warning-color, #ffa600);
  }
  .pill.low .dot,
  .pill.info .dot {
    background: var(--disabled-text-color, #888);
  }
  .pill.good .dot {
    background: var(--success-color, #43a047);
  }
  .tag {
    font-size: 10.5px;
    padding: 2px 6px;
    border-radius: 5px;
    font-family: var(--ha-font-family-code, monospace);
  }
  .tag.enforced {
    background: rgba(67, 160, 71, 0.15);
    color: var(--success-color, #43a047);
  }
  .tag.cosmetic {
    background: rgba(255, 166, 0, 0.18);
    color: var(--warning-color, #ffa600);
  }
  .probe-error-notice {
    border-left: 4px solid var(--status-critical, #d03b3b);
    background: rgba(var(--rgb-error-color, 219, 68, 55), 0.06);
    border-radius: 4px;
    padding: 8px 12px;
    margin: 8px 0;
  }
  .probe-error-notice .probe-error-text {
    font-family: var(--ha-font-family-code, monospace);
    font-size: 12px;
    color: var(--status-critical, #d03b3b);
    word-break: break-word;
  }
  .probe-error-notice .probe-error-hint {
    font-size: 12px;
    margin-top: 6px;
  }
  .probe-error-notice .probe-error-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 10px;
  }
  button.ha-btn {
    font: inherit;
    font-weight: 500;
    font-size: 13px;
    color: var(--primary-color);
    background: none;
    border: 1px solid var(--primary-color);
    border-radius: 8px;
    padding: 6px 12px;
    cursor: pointer;
  }
  button.ha-btn:hover {
    background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.08);
  }
  button.ha-btn.danger {
    color: var(--error-color, #db4437);
    border-color: var(--error-color, #db4437);
  }
  button.ha-btn.ha-btn-active {
    color: var(--text-primary-color, #fff);
    background: var(--primary-color);
  }
  button.ha-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  input,
  select {
    font: inherit;
    font-size: 13px;
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .toolbar .spacer {
    flex: 1;
  }
  .empty {
    color: var(--secondary-text-color);
    font-size: 13px;
    padding: 24px 0;
    text-align: center;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .chip {
    font-size: 10.5px;
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
    padding: 2px 6px;
    border-radius: 5px;
  }
  .settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 10px 0;
    border-bottom: 1px solid var(--divider-color);
    font-size: 13.5px;
  }
  /* Visually separates two opposite-direction settings sub-sections sharing
     one card (e.g. Syslog Export vs. Syslog Receiver). */
  .syslog-subsection-divider {
    margin: 18px 0 10px;
    border-top: 2px dashed var(--divider-color);
  }
  .syslog-subsection-heading {
    margin: 0 0 4px;
    font-size: 13px;
    font-weight: 600;
    color: var(--secondary-text-color);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .settings-row:last-child {
    border-bottom: none;
  }
  .settings-row > span:first-child {
    color: var(--primary-text-color);
    flex: 1;
  }
  .settings-row input[type="number"],
  .settings-row input[type="password"],
  .settings-row input[type="text"] {
    width: 160px;
    text-align: right;
  }
  .settings-row select {
    min-width: 220px;
  }
  .fw-subhead {
    margin: 16px 0 6px;
    font-size: 12.5px;
    color: var(--secondary-text-color);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  /* Accessible sortable column headers (see sortable.ts): the whole header
     is a real button (keyboard focus + Enter/Space), aria-sort on the th
     conveys state to assistive tech, the arrow is decorative only. */
  th.sortable {
    padding: 0;
  }
  th.sortable .sort-btn {
    font: inherit;
    font-size: 11px;
    font-weight: inherit;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--secondary-text-color);
    background: none;
    border: none;
    padding: 8px 10px;
    width: 100%;
    text-align: left;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }
  th.sortable.num .sort-btn {
    justify-content: flex-end;
    text-align: right;
  }
  th.sortable .sort-btn:hover,
  th.sortable .sort-btn:focus-visible {
    color: var(--primary-color);
  }
  th.sortable .sort-arrow {
    opacity: 0.35;
    font-size: 10px;
  }
  th.sortable .sort-arrow.active {
    opacity: 1;
    color: var(--primary-color);
  }
`,Ye={order:[],hidden:[]};function Ge(e,t){const s=new Map(e.map(e=>[e.id,e])),i=new Set,r=[];for(const e of t.order){const t=s.get(e);t&&!i.has(e)&&(r.push(t),i.add(e))}for(const t of e)i.has(t.id)||(r.push(t),i.add(t.id));return r}let Xe=class extends ae{constructor(){super(...arguments),this.sections=[],this.layout=Ye,this._dragId=null}render(){const e=Ge(this.sections,this.layout),t=new Set(this.layout.hidden);return K`
      <div class="customize-list">
        <p class="customize-hint">
          Drag the handle, or use ▲/▼, to reorder. Hide a section to remove it from this
          page without losing its data — you can bring it back here anytime.
        </p>
        ${e.map((s,i)=>this._renderEditRow(s,i,e.length,t.has(s.id)))}
      </div>
    `}_renderEditRow(e,t,s,i){return K`
      <div
        class="customize-row ${i?"row-hidden":""} ${this._dragId===e.id?"dragging":""}"
        draggable="true"
        @dragstart=${t=>this._onDragStart(t,e.id)}
        @dragover=${e=>e.preventDefault()}
        @drop=${t=>this._onDrop(t,e.id)}
        @dragend=${()=>this._onDragEnd()}
      >
        <span class="handle" aria-hidden="true" title="Drag to reorder">⠿⠿</span>
        <span class="row-title">${e.title}</span>
        <button
          type="button"
          class="icon-btn"
          title="Move up"
          ?disabled=${0===t}
          @click=${()=>this._move(e.id,-1)}
        >
          ▲
        </button>
        <button
          type="button"
          class="icon-btn"
          title="Move down"
          ?disabled=${t===s-1}
          @click=${()=>this._move(e.id,1)}
        >
          ▼
        </button>
        ${!1===e.hideable?j:K`
              <button
                type="button"
                class="icon-btn ${i?"":"visibility-on"}"
                title=${i?"Show this section":"Hide this section"}
                @click=${()=>this._toggleHidden(e.id)}
              >
                ${i?"Show":"Hide"}
              </button>
            `}
      </div>
    `}_move(e,t){const s=Ge(this.sections,this.layout).map(e=>e.id),i=s.indexOf(e),r=i+t;i<0||r<0||r>=s.length||([s[i],s[r]]=[s[r],s[i]],this._emitChange(s,this.layout.hidden))}_toggleHidden(e){const t=this.layout.hidden.includes(e)?this.layout.hidden.filter(t=>t!==e):[...this.layout.hidden,e],s=Ge(this.sections,this.layout).map(e=>e.id);this._emitChange(s,t)}_onDragStart(e,t){this._dragId=t,e.dataTransfer?.setData("text/plain",t),e.dataTransfer&&(e.dataTransfer.effectAllowed="move"),this.requestUpdate()}_onDrop(e,t){e.preventDefault();const s=this._dragId;if(!s||s===t)return;const i=Ge(this.sections,this.layout).map(e=>e.id),r=i.indexOf(s),n=i.indexOf(t);r<0||n<0||(i.splice(r,1),i.splice(n,0,s),this._emitChange(i,this.layout.hidden))}_onDragEnd(){this._dragId=null,this.requestUpdate()}_emitChange(e,t){this.dispatchEvent(new CustomEvent("layout-change",{detail:{order:e,hidden:t},bubbles:!0,composed:!0}))}};Xe.styles=a`
    :host {
      display: block;
    }
    .customize-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 16px;
      padding: 10px;
      border-radius: var(--ha-card-border-radius, 12px);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.06);
      border: 1px dashed rgba(var(--rgb-primary-color, 3, 155, 229), 0.35);
    }
    .customize-hint {
      font-size: 12px;
      color: var(--secondary-text-color);
      margin: 0 0 4px 2px;
    }
    .customize-row {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 8px 10px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    }
    .customize-row.dragging {
      opacity: 0.4;
    }
    .customize-row.row-hidden {
      opacity: 0.55;
    }
    .handle {
      cursor: grab;
      color: var(--secondary-text-color);
      font-size: 16px;
      line-height: 1;
      user-select: none;
    }
    .row-title {
      flex: 1;
      font-size: 13.5px;
      font-weight: 600;
    }
    .row-hidden .row-title {
      text-decoration: line-through;
      color: var(--secondary-text-color);
    }
    .icon-btn {
      background: none;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      padding: 3px 8px;
      color: var(--primary-text-color);
    }
    .icon-btn:hover {
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.05);
    }
    .icon-btn:disabled {
      opacity: 0.3;
      cursor: default;
    }
    .icon-btn.visibility-on {
      color: var(--primary-color);
      border-color: var(--primary-color);
    }
  `,e([ue({attribute:!1})],Xe.prototype,"sections",void 0),e([ue({attribute:!1})],Xe.prototype,"layout",void 0),Xe=e([he("ha-soc-customize-list")],Xe);class Je extends ae{constructor(){super(...arguments),this.customizeMode=!1,this._layout=Ye,this._onLayoutChange=e=>{var t,s,i;this._layout=e.detail,(t=this.hass,s=this.viewId,i=e.detail,we(t,{type:"ha_soc/layout/set",view_id:s,order:i.order,hidden:i.hidden})).catch(()=>{})}}connectedCallback(){super.connectedCallback(),this._loadLayout()}async _loadLayout(){try{this._layout=await(e=this.hass,t=this.viewId,we(e,{type:"ha_soc/layout/get",view_id:t}))}catch{this._layout=Ye}var e,t}_renderSections(e){if(this.customizeMode)return K`
        <ha-soc-customize-list
          .sections=${e}
          .layout=${this._layout}
          @layout-change=${this._onLayoutChange}
        ></ha-soc-customize-list>
      `;const t=new Set(this._layout.hidden);return K`${Ge(e,this._layout).filter(e=>!t.has(e.id)).map(e=>e.render())}`}}function Ze(e,t,s){if(!t)return e;const i=s[t.key];return i?e.map((e,t)=>({row:e,i:t})).sort((e,s)=>{const r=i(e.row),n=i(s.row),o=null==r||""===r,a=null==n||""===n;if(o&&a)return e.i-s.i;if(o)return 1;if(a)return-1;let l;return l="number"==typeof r&&"number"==typeof n?r-n:"boolean"==typeof r&&"boolean"==typeof n?Number(r)-Number(n):String(r).localeCompare(String(n),void 0,{sensitivity:"base",numeric:!0}),0!==l?l*t.dir:e.i-s.i}).map(e=>e.row):e}function Qe(e,t,s,i,r={}){const n=s?.key===t,o=n?1===s.dir?"ascending":"descending":"none",a=n?1===s.dir?"▲":"▼":"⇅";return K`
    <th class="sortable ${r.numeric?"num":""}" aria-sort=${o}>
      <button
        type="button"
        class="sort-btn"
        title="Sort by ${e}"
        @click=${()=>i(function(e,t){return e?.key===t?{key:t,dir:1===e.dir?-1:1}:{key:t,dir:1}}(s,t))}
      >
        ${e}<span class="sort-arrow ${n?"active":""}" aria-hidden="true">${a}</span>
      </button>
    </th>
  `}e([ue({attribute:!1})],Je.prototype,"hass",void 0),e([ue({type:Boolean})],Je.prototype,"customizeMode",void 0),e([pe()],Je.prototype,"_layout",void 0);let et=class extends Je{constructor(){super(...arguments),this._users=[],this._risk={},this._loading=!0,this._error=null,this._busyUserId=null,this._sort=null,this._pwUserId=null,this._pwValue="",this._pwKeepSessions=!1,this._pwError=null,this._pwNotice=null,this._isOwner=!1}get viewId(){return"users"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{const[e,t,s]=await Promise.all([Se(this.hass),xe(this.hass),Me(this.hass).catch(()=>({is_owner:!1}))]);this._users=e,this._risk=t,this._isOwner=!!s.is_owner}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}}_adminTargetLocked(e){return!this._isOwner&&(e.is_owner||e.groups.includes("system-admin"))}_fmtDate(e){if(!e)return"never";return new Date(e).toLocaleString()}async _onDeactivate(e){if(confirm("Deactivate this user? All their sessions will be revoked.")){this._busyUserId=e;try{await((e,t)=>we(e,{type:"ha_soc/users/deactivate",user_id:t}))(this.hass,e),await this._load()}finally{this._busyUserId=null}}}async _onRevokeAll(e){if(confirm("Revoke every interactive session for this user? Long-lived tokens are kept.")){this._busyUserId=e;try{await((e,t)=>we(e,{type:"ha_soc/users/revoke_all_sessions",user_id:t}))(this.hass,e),await this._load()}finally{this._busyUserId=null}}}_onToggleResetPanel(e){this._pwUserId=this._pwUserId===e?null:e,this._pwValue="",this._pwKeepSessions=!1,this._pwError=null,this._pwNotice=null}async _onSubmitPassword(e){if(this._pwValue){this._busyUserId=e,this._pwError=null,this._pwNotice=null;try{const t=await((e,t,s,i)=>we(e,{type:"ha_soc/users/set_password",user_id:t,password:s,revoke_sessions:i}))(this.hass,e,this._pwValue,!this._pwKeepSessions);this._pwNotice=t.sessions_revoked>0?`Password set. ${t.sessions_revoked} interactive session${1===t.sessions_revoked?"":"s"} revoked; long-lived tokens were kept.`:this._pwKeepSessions?"Password set. Existing sessions were kept at your request.":"Password set. No interactive sessions were active.",this._pwUserId=null,this._pwValue="",this._pwKeepSessions=!1}catch(e){this._pwError=e?.message??"Could not set the password."}finally{this._busyUserId=null}}}_renderPasswordPanel(e){return K`
      <tr>
        <td colspan="7" style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.03);">
          <div style="display:flex;flex-direction:column;gap:8px;max-width:560px;">
            <div style="font-weight:600;font-size:13px;">
              Set a new password for ${e.name??e.id}
            </div>
            <div class="muted" style="font-size:12.5px;line-height:1.5;">
              Setting the password also revokes every interactive session this user
              holds, so anyone signed in with the old password is signed out
              immediately. Long-lived access tokens are kept either way. Owner-only
              action, recorded in the audit log.
            </div>
            <input
              type="password"
              autocomplete="new-password"
              placeholder="New password"
              style="max-width:280px;"
              .value=${this._pwValue}
              @input=${e=>this._pwValue=e.target.value}
            />
            <label
              style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;"
            >
              <input
                type="checkbox"
                .checked=${this._pwKeepSessions}
                @change=${e=>this._pwKeepSessions=e.target.checked}
              />
              Also keep this user's current sessions (not recommended: whoever holds
              the old password stays signed in)
            </label>
            ${this._pwError?K`<div style="color:var(--error-color,#db4437);font-size:12.5px;">
                  ${this._pwError}
                </div>`:j}
            <div class="toolbar" style="margin:0;">
              <button
                class="ha-btn"
                ?disabled=${!this._pwValue||this._busyUserId===e.id}
                @click=${()=>this._onSubmitPassword(e.id)}
              >
                ${this._busyUserId===e.id?"Setting…":"Set password"}
              </button>
              <button class="ha-btn" @click=${()=>this._onToggleResetPanel(e.id)}>Cancel</button>
            </div>
          </div>
        </td>
      </tr>
    `}render(){if(this._loading)return K`<div class="empty">Loading users…</div>`;if(this._error)return K`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Users &amp; Access</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;if(!this._users.length)return K`<div class="empty">No users found.</div>`;const e=this._sort,t=e=>{this._sort=e},s=Ze(this._users,e,{user:e=>e.name??e.id,role:e=>`${e.is_admin?"Admin":"User"}${e.local_only?" · local only":""}`,mfa:e=>e.mfa_enabled,risk:e=>this._risk[e.id]?.score??null,last_login:e=>e.last_login_at?Date.parse(e.last_login_at):null,tokens:e=>e.llat_count}),i=[{id:"users",title:"Users & Access",hideable:!1,render:()=>K`
      <div class="card">
        <h3>Users &amp; Access</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Last login is derived from refresh-token activity — a background token
          refresh looks the same as a fresh interactive login. MFA status is read
          directly from the auth store but cannot be enforced by Home Assistant.
        </p>
        ${this._pwNotice?K`<p class="muted" style="font-size:12.5px;">${this._pwNotice}</p>`:j}
        <table>
          <thead>
            <tr>
              ${Qe("User","user",e,t)}
              ${Qe("Role","role",e,t)}
              ${Qe("MFA","mfa",e,t)}
              ${Qe("Risk","risk",e,t)}
              ${Qe("Last login","last_login",e,t)}
              ${Qe("Tokens","tokens",e,t)}
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${s.map(e=>{const t=this._risk[e.id];return K`
                <tr class=${e.is_active?"":"row-disabled"}>
                  <td>
                    <div>${e.name??e.id}</div>
                    ${e.is_owner?K`<span class="tag enforced">owner</span>`:j}
                    ${e.is_active?j:K`<span class="tag cosmetic">deactivated</span>`}
                  </td>
                  <td>${e.is_admin?"Admin":"User"}${e.local_only?" · local only":""}</td>
                  <td>
                    ${e.mfa_enabled?K`<span class="pill good"><span class="dot"></span>enabled</span>`:!1===e.mfa_assessable?K`<span
                            class="muted"
                            title="Every credential this user has comes from an external auth provider (SSO/header proxy, trusted networks, or a command-line provider). Home Assistant cannot see a second factor enforced upstream, so MFA cannot be assessed for this account."
                            >not assessable</span
                          >`:K`<span class="pill high"><span class="dot"></span>none</span>`}
                  </td>
                  <td>
                    ${t?K`<span class="pill ${"critical"===t.band||"high"===t.band?"high":"moderate"===t.band?"medium":"good"}">
                          <span class="dot"></span>${t.score}
                        </span>`:K`<span class="muted">—</span>`}
                  </td>
                  <td>
                    <div>${this._fmtDate(e.last_login_at)}</div>
                    ${e.last_login_ip?K`<div class="muted">${e.last_login_ip}</div>`:j}
                  </td>
                  <td>
                    ${e.llat_count>0?K`<span class="chip">${e.llat_count} long-lived</span>`:K`<span class="muted">none</span>`}
                  </td>
                  <td>
                    <div class="toolbar" style="margin:0;">
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId===e.id||e.is_owner}
                        @click=${()=>this._onToggleResetPanel(e.id)}
                      >
                        ${this._pwUserId===e.id?"Close":"Reset password"}
                      </button>
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId===e.id||this._adminTargetLocked(e)}
                        title=${this._adminTargetLocked(e)?"This user is in the admin group; only the account owner can revoke an administrator's sessions.":""}
                        @click=${()=>this._onRevokeAll(e.id)}
                      >
                        Revoke sessions
                      </button>
                      <button
                        class="ha-btn danger"
                        ?disabled=${this._busyUserId===e.id||e.is_owner||this._adminTargetLocked(e)}
                        title=${this._adminTargetLocked(e)?"This user is in the admin group; only the account owner can deactivate an administrator.":""}
                        @click=${()=>this._onDeactivate(e.id)}
                      >
                        Deactivate
                      </button>
                    </div>
                  </td>
                </tr>
                ${this._pwUserId===e.id?this._renderPasswordPanel(e):j}
              `})}
          </tbody>
        </table>
      </div>
        `}];return this._renderSections(i)}};et.styles=qe,e([pe()],et.prototype,"_users",void 0),e([pe()],et.prototype,"_risk",void 0),e([pe()],et.prototype,"_loading",void 0),e([pe()],et.prototype,"_error",void 0),e([pe()],et.prototype,"_busyUserId",void 0),e([pe()],et.prototype,"_sort",void 0),e([pe()],et.prototype,"_pwUserId",void 0),e([pe()],et.prototype,"_pwValue",void 0),e([pe()],et.prototype,"_pwKeepSessions",void 0),e([pe()],et.prototype,"_pwError",void 0),e([pe()],et.prototype,"_pwNotice",void 0),e([pe()],et.prototype,"_isOwner",void 0),et=e([he("ha-soc-users-view")],et);const tt=[["","All categories"],["service_call","Service call"],["login_ok","Login OK"],["login_fail","Login failed"],["token_created","Token created"],["session_seen","Session first seen"],["user_added","User added"],["user_updated","User updated"],["user_removed","User removed"],["lovelace_change","Dashboard edit"],["dashboard_panels_change","Panel set changed"],["entity_registry_change","Entity registry"],["device_registry_change","Device registry"],["area_registry_change","Area registry"],["floor_registry_change","Floor registry"],["label_registry_change","Label registry"],["category_registry_change","Category registry"],["config_entry_change","Config entry"],["core_config_change","Core config"],["watchdog_triggered","Watchdog triggered"],["soc_config_change","SOC config change"],["dashboard_file_write","Dashboard file written"],["dashboard_file_denied","Dashboard file refused"]];let st=class extends Je{constructor(){super(...arguments),this._events=[],this._users=[],this._loading=!0,this._error=null,this._category="",this._userId="",this._verifyResult=null,this._sort=null,this._stats=null}get viewId(){return"audit"}connectedCallback(){super.connectedCallback(),this._loadUsers(),this._load()}async _loadUsers(){this._users=await Se(this.hass)}async _load(){this._loading=!0,this._error=null;try{this._events=await((e,t={})=>we(e,{type:"ha_soc/audit/query",...t}).then(e=>e.events))(this.hass,{category:this._category||void 0,user_id:this._userId||void 0,limit:200})}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}}_nameFor(e){return e?this._users.find(t=>t.id===e)?.name??e:"—"}async _onVerify(){var e;this._verifyResult=await(e=this.hass,we(e,{type:"ha_soc/audit/verify_chain"}))}async _onCategoryStats(){var e;this._stats=await(e=this.hass,we(e,{type:"ha_soc/audit/category_stats"}))}_onCategoryChange(e){this._category=e.target.value,this._load()}_onUserChange(e){this._userId=e.target.value,this._load()}render(){const e=this._sort,t=e=>{this._sort=e},s=Ze(this._events,e,{time:e=>Date.parse(e.ts),category:e=>e.category,user:e=>e.user_id?this._nameFor(e.user_id):null,action:e=>e.domain?`${e.domain}.${e.service}${e.entity_ids?.length?` (${e.entity_ids.join(", ")})`:""}`:null,source:e=>e.ip}),i=[{id:"audit",title:"Audit Log",hideable:!1,render:()=>K`
      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every user-attributed service call, user/dashboard change, and
          best-effort login signal. Failed logins carry only a source IP — Home
          Assistant never logs the attempted username on a failed login.
        </p>
        <div class="toolbar">
          <select @change=${this._onCategoryChange}>
            ${tt.map(([e,t])=>K`<option value=${e} ?selected=${e===this._category}>${t}</option>`)}
          </select>
          <select @change=${this._onUserChange}>
            <option value="" ?selected=${""===this._userId}>All users</option>
            ${this._users.map(e=>K`<option value=${e.id} ?selected=${e.id===this._userId}>${e.name??e.id}</option>`)}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onVerify}>Verify chain integrity</button>
          <button class="ha-btn" @click=${this._onCategoryStats}>Volume by category</button>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._stats?K`<p class="muted" style="font-size:12px;">
              ${this._stats.day?K`${this._stats.day}: ${this._stats.total_records.toLocaleString()} records,
                  ${(this._stats.total_bytes/1024).toFixed(0)} KB.
                  ${this._stats.categories.slice(0,6).map(e=>`${e.category} ${e.records.toLocaleString()} (${Math.round(100*e.byte_share)}%)`).join(" · ")}${this._stats.categories.length>6?" · …":""}`:"No audit day files yet."}
            </p>`:null}
        ${this._verifyResult?K`<p class="${this._verifyResult.ok?"muted":""}" style="font-size:12.5px;">
              ${this._verifyResult.ok?(this._verifyResult.verified_from_seq??1)>1?`Chain intact - ${this._verifyResult.records_checked} records checked. Verified from record ${this._verifyResult.verified_from_seq}; records before ${this._verifyResult.expired_through??"the retention cutoff"} expired under retention.`:`Chain intact - ${this._verifyResult.records_checked} records checked.`:"Chain broken - see logs for the first mismatched record."}
            </p>`:null}
        ${this._loading?K`<div class="empty">Loading…</div>`:this._error?K`
              <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
                <p style="font-size:13px;margin:0 0 8px;">${this._error}</p>
                <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
              </div>
            `:this._events.length?K`
              <table>
                <thead>
                  <tr>
                    ${Qe("Time","time",e,t)}
                    ${Qe("Category","category",e,t)}
                    ${Qe("User","user",e,t)}
                    ${Qe("Action","action",e,t)}
                    ${Qe("Source","source",e,t)}
                  </tr>
                </thead>
                <tbody>
                  ${s.map(e=>K`
                      <tr>
                        <td>${new Date(e.ts).toLocaleString()}</td>
                        <td><span class="tag cosmetic">${e.category}</span></td>
                        <td>${this._nameFor(e.user_id)}</td>
                        <td>${e.domain?`${e.domain}.${e.service}`:""} ${e.entity_ids?.length?`(${e.entity_ids.join(", ")})`:""}</td>
                        <td>${e.ip??"—"}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:K`<div class="empty">No matching events.</div>`}
      </div>
        `}];return this._renderSections(i)}};st.styles=qe,e([pe()],st.prototype,"_events",void 0),e([pe()],st.prototype,"_users",void 0),e([pe()],st.prototype,"_loading",void 0),e([pe()],st.prototype,"_error",void 0),e([pe()],st.prototype,"_category",void 0),e([pe()],st.prototype,"_userId",void 0),e([pe()],st.prototype,"_verifyResult",void 0),e([pe()],st.prototype,"_sort",void 0),e([pe()],st.prototype,"_stats",void 0),st=e([he("ha-soc-audit-view")],st);let it=class extends Je{constructor(){super(...arguments),this._users=[],this._dashboards=[],this._selected=void 0,this._views=[],this._loading=!0,this._error=null,this._drift=[],this._viewsError=null,this._writeError=null,this._sort=null}get viewId(){return"permissions"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{const[t,s]=await Promise.all([Se(this.hass),(e=this.hass,we(e,{type:"ha_soc/permissions/dashboards/list"}).then(e=>e.dashboards))]);this._users=t.filter(e=>e.is_active),this._dashboards=s,void 0===this._selected&&s.length&&(this._selected=s[0].url_path??null),void 0!==this._selected&&await this._loadViews()}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}var e}async _loadViews(){this._viewsError=null;try{const s=await(e=this.hass,t=this._selected??null,we(e,{type:"ha_soc/permissions/dashboard_config",url_path:t}).then(e=>e.config)),i=s?.views??[];this._views=i.map((e,t)=>({path:e.path??String(t),title:e.title??e.path??`View ${t+1}`,visibleUserIds:Array.isArray(e.visible)?e.visible.map(e=>e.user):null}))}catch(e){this._views=[],this._viewsError="not_found"===e?.code?"This dashboard has no saved layout yet — Home Assistant is showing an auto-generated default until someone opens and customizes it in the dashboard editor. There's nothing here for the permissions matrix to manage until then.":`Could not load this dashboard's views: ${e?.message??e}`}var e,t}async _onSelectDashboard(e){const t=e.target.value;this._selected="__default__"===t?null:t,await this._loadViews()}async _onToggleUser(e,t,s){const i=e.target,r=t.visibleUserIds??this._users.map(e=>e.id),n=r.includes(s),o=n?r.filter(e=>e!==s):[...r,s],a=o.length===this._users.length?[]:o;this._writeError=null;try{await((e,t,s,i)=>we(e,{type:"ha_soc/permissions/view_visibility/set",url_path:t,view_path:s,user_ids:i}))(this.hass,this._selected??null,t.path,a),await this._loadViews()}catch(e){i.checked=n,this._writeError=`The visibility change for "${t.title}" was rejected: ${e?.message??e?.code??"unknown error"}. The checkbox was restored to the saved state.`}}async _onToggleFlag(e,t,s,i){const r=e.target;this._writeError=null;try{await((e,t,s)=>we(e,{type:"ha_soc/permissions/dashboard_flags/set",dashboard_id:t,...s}))(this.hass,t,{[s]:i}),await this._load()}catch(e){r.checked=!i,this._writeError=`The ${s} change was rejected: ${e?.message??e?.code??"unknown error"}. The checkbox was restored to the saved state.`}}async _onCheckDrift(){this._writeError=null;try{this._drift=await(e=this.hass,we(e,{type:"ha_soc/permissions/drift/check"}).then(e=>e.drift))}catch(e){this._writeError=`Drift check failed: ${e?.message??e}`}var e}render(){if(this._loading)return K`<div class="empty">Loading dashboards…</div>`;if(this._error)return K`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the Permissions Matrix</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const e=this._dashboards.find(e=>(e.url_path??null)===(this._selected??null)),t=[{id:"permissions",title:"Permissions Matrix",hideable:!1,render:()=>K`
      <div class="card">
        <h3>Permissions Matrix</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">UI-only</span> View/card visibility and
          <code>require_admin</code> change what a user's own frontend renders — any
          authenticated user can still fetch a dashboard's full config over the
          websocket API. The only real access-control lever is a user's
          admin/non-admin group, managed in the Users &amp; Access tab.
        </p>
        <div class="toolbar">
          <select .value=${this._selected??"__default__"} @change=${this._onSelectDashboard}>
            ${this._dashboards.map(e=>K`<option value=${e.url_path??"__default__"}>
                  ${e.title??e.url_path??"Overview"}
                </option>`)}
          </select>
          ${e?K`
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!!e.require_admin}
                    @change=${t=>this._onToggleFlag(t,e.id,"require_admin",t.target.checked)}
                  />
                  require_admin
                </label>
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!1!==e.show_in_sidebar}
                    @change=${t=>this._onToggleFlag(t,e.id,"show_in_sidebar",t.target.checked)}
                  />
                  show in sidebar
                </label>
              `:j}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onCheckDrift}>Check drift</button>
        </div>

        ${this._writeError?K`<p style="font-size:12.5px;color:var(--error-color,#db4437);">
              ${this._writeError}
            </p>`:j}
        ${this._drift.length?K`<p style="font-size:12.5px;color:var(--warning-color);">
              ${this._drift.length} view(s) no longer match the policy last applied here — likely edited directly in the dashboard editor.
            </p>`:j}

        ${this._views.length?(()=>{const e={view:e=>e.title};for(const t of this._users)e[`user:${t.id}`]=e=>null===e.visibleUserIds||e.visibleUserIds.includes(t.id);const t=Ze(this._views,this._sort,e),s=this._sort,i=e=>this._sort=e;return K`
              <table>
                <thead>
                  <tr>
                    ${Qe("View","view",s,i)}
                    ${this._users.map(e=>Qe(e.name??e.id,`user:${e.id}`,s,i))}
                  </tr>
                </thead>
                <tbody>
                  ${t.map(e=>K`
                      <tr>
                        <td>${e.title}</td>
                        ${this._users.map(t=>{const s=null===e.visibleUserIds||e.visibleUserIds.includes(t.id);return K`
                            <td>
                              <input
                                type="checkbox"
                                .checked=${s}
                                @change=${s=>this._onToggleUser(s,e,t.id)}
                              />
                            </td>
                          `})}
                      </tr>
                    `)}
                </tbody>
              </table>
            `})():K`<div class="empty">
              ${this._viewsError??"This dashboard has no views, or is YAML-managed (read-only)."}
            </div>`}
      </div>
        `}];return this._renderSections(t)}};var rt;it.styles=qe,e([pe()],it.prototype,"_users",void 0),e([pe()],it.prototype,"_dashboards",void 0),e([pe()],it.prototype,"_selected",void 0),e([pe()],it.prototype,"_views",void 0),e([pe()],it.prototype,"_loading",void 0),e([pe()],it.prototype,"_error",void 0),e([pe()],it.prototype,"_drift",void 0),e([pe()],it.prototype,"_viewsError",void 0),e([pe()],it.prototype,"_writeError",void 0),e([pe()],it.prototype,"_sort",void 0),it=e([he("ha-soc-permissions-view")],it);const nt=["new","confirmed","dismissed","resolved"],ot=["critical","high","medium","low","info"];function at(e){const t=ot.indexOf(e);return-1===t?ot.length:t}function lt(e,t){const s=e.indexOf(String(t));return-1===s?null:s}const ht=["high","medium","advisory"],ct=["exact_cpe","curated_map","keyword","heuristic"];function dt(e){return"4"===e?"IPv4":"6"===e?"IPv6":"IPv4+IPv6"}const ut=/^[0-9]{1,5}(:[0-9]{1,5})?(,[0-9]{1,5}(:[0-9]{1,5})?)*$/,pt=/^[A-Za-z0-9_.:@-]{1,15}$/,_t=/^[A-Za-z0-9_.-]{1,22}$/,ft=[[8123,"Home Assistant"],[443,"HTTPS"],[80,"HTTP"],[22,"SSH add-on"],[1883,"MQTT"],[5353,"mDNS (udp)"],[21064,"HomeKit"],[445,"Samba"],[8443,"HTTPS alternate"]];function gt(e){return"icmp"===e.proto?`icmp ${e.icmp_type&&"any"!==e.icmp_type?e.icmp_type:"any type"}`:`${e.proto}/${e.ports??e.port??"?"}`}function vt(e){const t=[];return e.log&&t.push("log"),e.comment&&t.push(`#${e.comment}`),t.join(" · ")}function mt(e){return"allow"===e?"good":"critical"}function yt(e,t){return wt(e)??wt(t)}function bt(e){const t=me.find(([t])=>t===(e??"any"));return t?null===t[1]&&null!==t[2]?"6":null===t[2]&&null!==t[1]?"4":null:null}function wt(e){return e?e.includes(":")?"6":"4":null}function St(e){return"0.0.0.0"===e?{priority:0,label:"all interfaces",cls:"high"}:e?e.startsWith("127.")||e.startsWith("169.254.")?{priority:3,label:"loopback / link-local",cls:"good"}:function(e){const t=e.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);if(!t)return!1;const[s,i]=[Number(t[1]),Number(t[2])];return 10===s||172===s&&i>=16&&i<=31||192===s&&168===i}(e)?{priority:2,label:"private (RFC 1918)",cls:"low"}:{priority:1,label:"public / routable",cls:"high"}:{priority:4,label:"unresolved (IPv6)",cls:"info"}}let xt=rt=class extends Je{constructor(){super(...arguments),this._scannerFindings=[],this._coverage=null,this._vulnFindings=[],this._misconfigFindings=[],this._probe=null,this._loading=!0,this._error=null,this._scanning=!1,this._scanError=null,this._exportNotice=null,this._firewall=null,this._fwDraftRules=[rt._emptyDraftRule()],this._fwBackupAck=!1,this._fwSubmitting=!1,this._fwError=null,this._fwPollHandle=null,this._isOwner=!1,this._fwNetworks=[],this._netscan=null,this._netscanRescanSubmitting=!1,this._netscanError=null,this._misconfigSort=null,this._scannerSort=null,this._vulnSort=null,this._portSort=null,this._fwRulesSort=null,this._coverageSort=null,this._netscanSort=null,this._openResolved=new Set}get viewId(){return"scanner"}static _emptyDraftRule(){return{action:"allow",proto:"tcp",ports:"",icmp_type:"any",source:"",destination:"",interface:"",log:!1,comment:"",family:"both"}}connectedCallback(){super.connectedCallback(),this._load()}disconnectedCallback(){super.disconnectedCallback(),null!==this._fwPollHandle&&(window.clearInterval(this._fwPollHandle),this._fwPollHandle=null)}async _load(){this._loading=!0,this._error=null;try{const[t,s,i,r,n]=await Promise.all([(e=this.hass,we(e,{type:"ha_soc/scanner/list"})),Ee(this.hass),Te(this.hass),Be(this.hass),Me(this.hass).catch(()=>({is_owner:!1}))]);this._scannerFindings=t.findings,this._coverage=t.coverage??null,this._vulnFindings=s,this._misconfigFindings=i.misconfig_findings,this._probe=r,this._isOwner=!!n.is_owner,this._firewall=this._isOwner?await Oe(this.hass).catch(()=>null):null,this._netscan=this._isOwner?await ze(this.hass).catch(()=>null):null,this._fwNetworks=this._isOwner?await He(this.hass).then(e=>e.networks??[]).catch(()=>[]):[],this._maybeManageFirewallPolling()}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}var e}_maybeManageFirewallPolling(){const e=null!=this._firewall?.pending;e&&null===this._fwPollHandle?this._fwPollHandle=window.setInterval(()=>this._pollFirewallStatus(),2e3):e||null===this._fwPollHandle||(window.clearInterval(this._fwPollHandle),this._fwPollHandle=null)}async _pollFirewallStatus(){this._applyFirewallStatus(await Oe(this.hass))}_applyFirewallStatus(e){const t=null!=this._firewall?.pending;this._firewall=e,t&&!e.pending&&(this._fwBackupAck=!1),this._maybeManageFirewallPolling()}_fwRuleValid(e){const t=e.family??"both",s=yt(e.source??"",e.destination??""),i=wt(e.source??""),r=wt(e.destination??"");if(i&&r&&i!==r)return!1;if(e.source&&!i||e.destination&&!r)return!1;if("icmp"===e.proto){if(!me.some(([t])=>t===(e.icmp_type??"any")))return!1;const t=bt(e.icmp_type);if(t&&s&&t!==s)return!1;if(!this._fwCapable("icmp"))return!1}else{if(!function(e){if(!ut.test(e))return!1;const t=e.split(",");return!(t.length>15)&&t.every(e=>{const[t,s]=e.split(":"),i=Number(t),r=void 0===s?i:Number(s);return!(i<1||i>65535||r<1||r>65535)&&(void 0===s||r>i)})}(e.ports??""))return!1;if((e.ports??"").includes(",")&&!this._fwCapable("multiport"))return!1}return!(e.interface&&!pt.test(e.interface))&&(!!(!e.comment||_t.test(e.comment)&&this._fwCapable("comment"))&&(!!(!e.log||this._fwCapable("log")&&this._fwCapable("limit"))&&(!("reject"===e.action&&!this._fwCapable("reject"))&&!("allow"!==e.action&&"deny"!==e.action&&"reject"!==e.action||"tcp"!==e.proto&&"udp"!==e.proto&&"icmp"!==e.proto||"4"!==t&&"6"!==t&&"both"!==t||null!==s&&s!==t))))}_fwUpdateRule(e,t){this._fwDraftRules=this._fwDraftRules.map((s,i)=>i===e?{...s,...t}:s)}_fwAddRule(){this._fwDraftRules=[...this._fwDraftRules,rt._emptyDraftRule()]}_fwRemoveRule(e){this._fwDraftRules=this._fwDraftRules.filter((t,s)=>s!==e)}static _interfaceForDraft(e){return e&&"(all interfaces)"!==e&&"unresolved"!==e?e:""}_onAddFirewallRuleForPort(e){const t=rt._emptyDraftRule(),s={...t,proto:e.proto,ports:String(e.port),interface:rt._interfaceForDraft(e.interface)},i=1===this._fwDraftRules.length?this._fwDraftRules[0]:null,r=!!i&&Object.keys(t).every(e=>i[e]===t[e]);this._fwDraftRules=r?[s]:[...this._fwDraftRules,s],this.updateComplete.then(()=>{this.renderRoot.querySelector("#fw-rules-card")?.scrollIntoView({behavior:"smooth",block:"start"})})}async _onProposeTest(){this._fwError=null,this._fwSubmitting=!0;try{const e=this._fwDraftRules.map(e=>({action:e.action,proto:e.proto,ports:"icmp"===e.proto?null:e.ports||null,icmp_type:"icmp"===e.proto?e.icmp_type||"any":null,source:e.source?e.source:null,destination:e.destination?e.destination:null,interface:e.interface?e.interface:null,log:!!e.log,comment:e.comment?e.comment:null,family:e.family??"both"}));await((e,t,s)=>we(e,{type:"ha_soc/firewall/test",rules:t,backup_acknowledged:s}))(this.hass,e,this._fwBackupAck),this._applyFirewallStatus(await Oe(this.hass))}catch(e){this._fwError=e?.message??"Failed to propose the firewall change."}finally{this._fwSubmitting=!1}}async _onConfirmTest(){if(this._firewall?.pending){this._fwError=null,this._fwSubmitting=!0;try{await(e=this.hass,t=this._firewall.pending.test_id,we(e,{type:"ha_soc/firewall/confirm",test_id:t})),this._applyFirewallStatus(await Oe(this.hass))}catch(e){this._fwError=e?.message??"Failed to confirm the firewall change."}finally{this._fwSubmitting=!1}var e,t}}async _onCancelTest(){if(this._firewall?.pending){this._fwError=null,this._fwSubmitting=!0;try{await(e=this.hass,t=this._firewall.pending.test_id,we(e,{type:"ha_soc/firewall/cancel",test_id:t})),this._applyFirewallStatus(await Oe(this.hass))}catch(e){this._fwError=e?.message??"Failed to cancel the firewall change."}finally{this._fwSubmitting=!1}var e,t}}async _onDiscardPending(){if(!this._firewall?.pending)return;if(confirm("Discard this unreported firewall test?\n\nThe add-on never reported its outcome, so HA SOC does not know what is live on the host. The record is archived as 'discarded_unreported' and new tests become possible again. Nothing is changed on the host by discarding.")){this._fwError=null,this._fwSubmitting=!0;try{await(e=this.hass,we(e,{type:"ha_soc/firewall/discard_pending"})),this._applyFirewallStatus(await Oe(this.hass))}catch(e){this._fwError=e?.message??"Failed to discard the pending firewall test."}finally{this._fwSubmitting=!1}var e}}async _onNetscanRescan(){this._netscanError=null,this._netscanRescanSubmitting=!0;try{await(e=this.hass,we(e,{type:"ha_soc/netscan/rescan"})),this._netscan=await ze(this.hass).catch(()=>this._netscan)}catch(e){this._netscanError=e?.message??"Failed to request a rescan."}finally{this._netscanRescanSubmitting=!1}var e}async _onScanIntegrations(){this._scanning=!0,this._scanError=null;try{await(e=this.hass,we(e,{type:"ha_soc/scanner/scan_now",domain:t})),await this._load()}catch(e){this._scanError=`Integration scan failed: ${e?.message??e}`}finally{this._scanning=!1}var e,t}async _onScanVulns(){this._scanning=!0,this._scanError=null;try{await(e=this.hass,we(e,{type:"ha_soc/vulns/scan_now"}).then(e=>e.findings)),await this._load()}catch(e){this._scanError=`Device vulnerability scan failed: ${e?.message??e}`}finally{this._scanning=!1}var e}async _onVulnStatus(e,t){this._scanError=null;try{await((e,t,s,i)=>we(e,{type:"ha_soc/vulns/set_status",finding_id:t,status:s,note:i}))(this.hass,e,t)}catch(e){this._scanError=`Status change failed: ${e?.message??e}`}await this._load()}async _onScannerStatus(e,t){this._scanError=null;try{await((e,t,s,i)=>we(e,{type:"ha_soc/scanner/set_status",finding_id:t,status:s,note:i}))(this.hass,e,t)}catch(e){this._scanError=`Status change failed: ${e?.message??e}`}await this._load()}async _onExportFinding(e){if(confirm(`Copy a GHSA-shaped advisory draft to the clipboard?\n\nIntegration: ${e.domain}\nMatched code: ${e.snippet}\n\nNothing is submitted anywhere. The text is only placed on your clipboard for you to review and paste yourself.`)){this._exportNotice=null;try{const i=await(t=this.hass,s=e.id,we(t,{type:"ha_soc/scanner/export",finding_id:s})),r=[`Title: ${i.title}`,`Severity: ${i.severity}`,`CWE: ${i.cwe}`,`Package: ${i.affected.package} (${i.affected.ecosystem})`,"",i.description].join("\n");await navigator.clipboard.writeText(r),this._exportNotice=`Copied the advisory draft for ${e.domain} (${e.file}:${e.line}) to the clipboard.`}catch(e){this._exportNotice=`Export failed: ${e?.message??"could not copy to the clipboard"}`}var t,s}}async _onMisconfigStatus(e,t){this._scanError=null;try{await((e,t,s,i)=>we(e,{type:"ha_soc/misconfig/set_status",finding_id:t,status:s,note:i}))(this.hass,e,t)}catch(e){this._scanError=`Status change failed: ${e?.message??e}`}await this._load()}_groupedVulnFindings(){return this._groupedVulnFindingsFrom(this._vulnFindings)}_groupedVulnFindingsFrom(e){const t=new Map;for(const s of e){const e=String(s.device_name??"Unknown device"),i=t.get(e);i?i.push(s):t.set(e,[s])}const s=this._vulnSort,i=Array.from(t.entries()).map(([e,t])=>({device_name:e,worst:Math.min(...t.map(e=>at(e.severity))),findings:s?Ze(t,s,rt.VULN_SORT):[...t].sort((e,t)=>at(e.severity)-at(t.severity))}));return"cve"===s?.key?i.sort((e,t)=>e.device_name.localeCompare(t.device_name,void 0,{sensitivity:"base",numeric:!0})*s.dir):i.sort((e,t)=>e.worst-t.worst),i}_renderScannerCoverage(){if(!this._coverage)return j;const e=new Set(Object.keys(this._coverage)),t=new Set(this._scannerFindings.map(e=>String(e.domain))),s=Array.from(t).filter(t=>!e.has(t)).sort((e,t)=>e.localeCompare(t)),i=Object.entries(this._coverage).map(([e,t])=>({domain:e,cov:t})),r=this._coverageSort?Ze(i,this._coverageSort,rt.COVERAGE_SORT):i.slice().sort((e,t)=>e.domain.localeCompare(t.domain));return K`
      <h4 class="fw-subhead">Scan coverage</h4>
      <p class="muted" style="font-size:12px;margin-top:-6px;">
        What the most recent completed pass over each domain actually looked at.
        A domain is never implied clean by an absent record.
      </p>
      ${i.length?K`
            <table>
              <thead>
                <tr>
                  ${Qe("Domain","domain",this._coverageSort,e=>this._coverageSort=e)}
                  ${Qe("Files scanned","files",this._coverageSort,e=>this._coverageSort=e,{numeric:!0})}
                  ${Qe("Skipped (too large)","oversize",this._coverageSort,e=>this._coverageSort=e,{numeric:!0})}
                  ${Qe("Skipped (over cap)","over_cap",this._coverageSort,e=>this._coverageSort=e,{numeric:!0})}
                  ${Qe("Parse failures","parse_failures",this._coverageSort,e=>this._coverageSort=e,{numeric:!0})}
                  ${Qe("Scanned at","scanned_at",this._coverageSort,e=>this._coverageSort=e)}
                </tr>
              </thead>
              <tbody>
                ${r.map(e=>K`
                    <tr>
                      <td>${e.domain}</td>
                      <td class="num">${e.cov.scanned_files}</td>
                      <td class="num">${e.cov.skipped_oversize}</td>
                      <td class="num">${e.cov.skipped_over_cap}</td>
                      <td class="num">${e.cov.parse_failures}</td>
                      <td>${new Date(e.cov.scanned_at).toLocaleString()}</td>
                    </tr>
                  `)}
              </tbody>
            </table>
          `:K`<div class="empty">No domain has completed a scan yet.</div>`}
      ${s.length?K`<p style="font-size:12.5px;margin-top:8px;">
            <strong>Not scanned this pass:</strong> ${s.join(", ")}.
            ${1===s.length?"Its":"Their"} existing findings above were not
            re-verified in the most recent run.
          </p>`:j}
    `}_resolvedStorageKey(e){return`ha-soc-scanner-resolved-open:${e}`}_isOpen(e){if(this._openResolved.has(e))return!0;try{if("true"===localStorage.getItem(this._resolvedStorageKey(e)))return this._openResolved.add(e),!0}catch{}return!1}_onToggle(e,t){const s=t.target.open;s?this._openResolved.add(e):this._openResolved.delete(e);try{localStorage.setItem(this._resolvedStorageKey(e),String(s))}catch{}}static _isResolvedStatus(e){return"resolved"===e||"dismissed"===e}static _splitByStatus(e){const t=[],s=[];for(const i of e)(rt._isResolvedStatus(i.status)?s:t).push(i);return{open:t,resolved:s}}_renderStatusSelect(e,t,s){return K`
      <select @change=${e=>s(e.target.value)}>
        ${nt.map(e=>K`<option value=${e} ?selected=${e===t}>${e}</option>`)}
      </select>
    `}_sortedMisconfigFindings(){return this._misconfigSort?Ze(this._misconfigFindings,this._misconfigSort,rt.MISCONFIG_SORT):[...this._misconfigFindings].sort((e,t)=>at(e.severity)-at(t.severity))}render(){if(this._loading)return K`<div class="empty">Loading findings…</div>`;if(this._error)return K`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the Scanner tab</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const e=[{id:"misconfig",title:"Misconfiguration Findings",render:()=>{const{open:e,resolved:t}=rt._splitByStatus(this._sortedMisconfigFindings()),s=e=>K`
            <tr>
              <td>${e.check}</td>
              <td><span class="pill ${e.severity}"><span class="dot"></span>${e.severity}</span></td>
              <td>${e.summary}</td>
              <td>
                ${e.acknowledged_by_design?K`<span class="tag enforced" title=${e.acknowledged_reason??"Acknowledged by design"}
                      >acknowledged by design</span
                    >`:this._renderStatusSelect(e.id,e.status,t=>this._onMisconfigStatus(e.id,t))}
              </td>
            </tr>
          `;return K`
      <div class="card">
        <h3>Misconfiguration Findings</h3>
        ${e.length?K`
              <table>
                <thead>
                  <tr>
                    ${Qe("Check","check",this._misconfigSort,e=>this._misconfigSort=e)}
                    ${Qe("Severity","severity",this._misconfigSort,e=>this._misconfigSort=e)}
                    ${Qe("Summary","summary",this._misconfigSort,e=>this._misconfigSort=e)}
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${e.map(s)}
                </tbody>
              </table>
            `:K`<div class="empty">No findings.</div>`}
        ${t.length?K`
              <details
                ?open=${this._isOpen("misconfig-resolved")}
                @toggle=${e=>this._onToggle("misconfig-resolved",e)}
              >
                <summary>Resolved (${t.length})</summary>
                <table>
                  <thead>
                    <tr>
                      <th>Check</th>
                      <th>Severity</th>
                      <th>Summary</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${t.map(s)}
                  </tbody>
                </table>
              </details>
            `:j}
      </div>
          `}},{id:"integration_scanner",title:"Integration Security Scanner",render:()=>K`
      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static AST/regex analysis of every installed integration's source — core and
          custom. Every finding is advisory and needs a human to confirm; Home
          Assistant's own quality tooling (hassfest) never checks for these patterns and
          never runs against custom_components at all. These rules find unobfuscated
          pattern instances only; a dynamically constructed call, a string-built
          decorator, or a renamed import will not be detected.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanIntegrations}>
            Scan all integrations now
          </button>
        </div>
        ${(()=>{const e=Ze(this._scannerFindings,this._scannerSort,rt.SCANNER_SORT),{open:t,resolved:s}=rt._splitByStatus(e),i=e=>K`
            <tr>
              <td>${e.domain}</td>
              <td><span class="pill ${e.severity}"><span class="dot"></span>${e.pattern}</span></td>
              <td>${e.file}:${e.line}</td>
              <td>${e.confidence}</td>
              <td>${e.cwe}</td>
              <td>${this._renderStatusSelect(e.id,e.status,t=>this._onScannerStatus(e.id,t))}</td>
              <td><button class="ha-btn" @click=${()=>this._onExportFinding(e)}>Export</button></td>
            </tr>
          `;return K`
            ${t.length?K`
                  <table>
                    <thead>
                      <tr>
                        ${Qe("Domain","domain",this._scannerSort,e=>this._scannerSort=e)}
                        ${Qe("Pattern","pattern",this._scannerSort,e=>this._scannerSort=e)}
                        ${Qe("Location","location",this._scannerSort,e=>this._scannerSort=e)}
                        ${Qe("Confidence","confidence",this._scannerSort,e=>this._scannerSort=e)}
                        ${Qe("CWE","cwe",this._scannerSort,e=>this._scannerSort=e)}
                        <th>Status</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      ${t.map(i)}
                    </tbody>
                  </table>
                  ${this._exportNotice?K`<p class="muted" style="font-size:12px;margin:6px 0 0;">${this._exportNotice}</p>`:j}
                `:K`<div class="empty">No findings.</div>`}
            ${s.length?K`
                  <details
                    ?open=${this._isOpen("scanner-resolved")}
                    @toggle=${e=>this._onToggle("scanner-resolved",e)}
                  >
                    <summary>Resolved (${s.length})</summary>
                    <table>
                      <thead>
                        <tr>
                          <th>Domain</th>
                          <th>Pattern</th>
                          <th>Location</th>
                          <th>Confidence</th>
                          <th>CWE</th>
                          <th>Status</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        ${s.map(i)}
                      </tbody>
                    </table>
                  </details>
                `:j}
          `})()}
        ${this._renderScannerCoverage()}
      </div>
        `},{id:"device_vulns",title:"Device Vulnerabilities",render:()=>K`
      <div class="card">
        <h3>Device Vulnerabilities</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Matches monitored devices against NVD by manufacturer/model — a heuristic
          match, never a confirmed exploit. Absence of a match is not evidence a device
          is secure.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanVulns}>
            Scan devices now
          </button>
        </div>
        ${(()=>{const{open:e,resolved:t}=rt._splitByStatus(this._vulnFindings),s=e=>K`
            ${e.map(e=>K`
                <tr>
                  <td colspan="4" style="font-weight:600;background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
                    ${e.device_name}
                    <span class="muted" style="font-weight:400;font-size:11.5px;"
                      >(${e.findings.length} finding${1===e.findings.length?"":"s"})</span
                    >
                  </td>
                </tr>
                ${e.findings.map(e=>K`
                    <tr>
                      <td>
                        ${e.cve_id?K`<a href="https://nvd.nist.gov/vuln/detail/${e.cve_id}" target="_blank" rel="noopener"
                              >${e.cve_id}</a
                            >`:"—"}
                      </td>
                      <td><span class="pill ${e.severity}"><span class="dot"></span>${e.cvss??"unscored"}</span></td>
                      <td>${e.confidence}</td>
                      <td>${this._renderStatusSelect(e.id,e.status,t=>this._onVulnStatus(e.id,t))}</td>
                    </tr>
                  `)}
              `)}
          `;return K`
            ${e.length?K`
                  <table>
                    <thead>
                      <tr>
                        ${Qe("CVE","cve",this._vulnSort,e=>this._vulnSort=e)}
                        ${Qe("CVSS","cvss",this._vulnSort,e=>this._vulnSort=e)}
                        ${Qe("Confidence","confidence",this._vulnSort,e=>this._vulnSort=e)}
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${s(this._groupedVulnFindingsFrom(e))}
                    </tbody>
                  </table>
                `:K`<div class="empty">No findings.</div>`}
            ${t.length?K`
                  <details
                    ?open=${this._isOpen("vulns-resolved")}
                    @toggle=${e=>this._onToggle("vulns-resolved",e)}
                  >
                    <summary>Resolved (${t.length})</summary>
                    <table>
                      <thead>
                        <tr>
                          <th>CVE</th>
                          <th>CVSS</th>
                          <th>Confidence</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${s(this._groupedVulnFindingsFrom(t))}
                      </tbody>
                    </table>
                  </details>
                `:j}
          `})()}
      </div>
        `},{id:"host_probe",title:"Host Probe",render:()=>this._renderProbeCard()},{id:"firewall_rules",title:"Firewall Rules",render:()=>this._renderFirewallCard()},{id:"netscan",title:"Network Scan",render:()=>this._renderNetscanCard()}];return K`
      ${this._scanError?K`<div class="card" style="border:1px solid var(--error-color,#db4437);">
            <p style="font-size:13px;color:var(--error-color,#db4437);margin:0;">${this._scanError}</p>
          </div>`:j}
      ${this._renderSections(e)}
    `}_renderProbeCard(){const e=this._probe;if(!e)return j;if(!e.supervisor)return K`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not available</span></h3>
          <p class="muted" style="font-size:12.5px;">
            Real socket-level port scanning of the host needs a companion add-on with
            host-network access — something a Python integration structurally cannot do
            on its own, even on Home Assistant OS. This install isn't running under
            Supervisor (Core/Container), so this feature has nothing to attach to here.
          </p>
        </div>
      `;if(!e.installed)return K`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not installed</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The optional <strong>HA SOC Probe</strong> add-on isn't installed. It's the
            only way to see the host's actual listening ports — this integration alone
            can't reach past its own container. Add its repository under
            Settings → Add-ons → Add-on Store → ⋮ → Repositories, then install
            "HA SOC Probe". See the README for the exact URL.
          </p>
        </div>
      `;const t=e.result;return K`
      <div class="card">
        <h3>
          Host Probe
          <span class="tag ${e.running?"enforced":"cosmetic"}">
            ${e.running?"running":"installed, not running"}
          </span>
          ${e.update_available?K`<span class="tag cosmetic">update available</span>`:j}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Version ${e.version??"unknown"}. Reports the host's real listening TCP
          ports — process-name attribution isn't included: identifying which process
          owns a port needs the add-on to also see the host's process list
          (<code>host_pid</code>), a privilege this add-on deliberately doesn't request.
        </p>
        ${t?K`
              <p class="muted" style="font-size:12px;">
                Last reported ${new Date(t.reported_at).toLocaleString()}
              </p>
              ${t.open_ports.length?this._renderPortsByBindAddress(t.open_ports):K`<div class="empty">No listening ports reported.</div>`}
            `:K`<div class="empty">No scan reported yet.</div>`}
      </div>
    `}_fwRuleCoveringPort(e){const t=this._firewall?.known_rules;if(!t?.length)return null;const s=e.address?"4":"6",i=t.filter(t=>{const i=t.family??"both";return t.proto===e.proto&&function(e,t){const s=e.ports??(e.port?String(e.port):"");return!!s&&s.split(",").some(e=>{const[s,i]=e.split(":"),r=Number(s),n=void 0===i?r:Number(i);return t>=r&&t<=n})}(t,e.port)&&("both"===i||i===s)});return i.length?(i.sort((e,t)=>e.action!==t.action?"deny"===e.action?-1:1:(e.source?1:0)-(t.source?1:0)),i[0]):null}_renderPortRuleCell(e){const t=this._fwRuleCoveringPort(e),s=e.address?"":" IPv6 bind addresses are not decoded by the add-on, so this correlation is by port and protocol only.";if(!t)return K`<td class="muted"><span title=${"No HA_SOC_RULES entry matches this port and protocol for this listener's address family."+s}>no rule</span></td>`;const i=t.source?`from ${t.source}`:"any source";return K`
      <td>
        <span
          class="pill ${mt(t.action)}"
          title=${`Covered by the ${t.action} ${gt(t)} rule (${dt(t.family)}, ${i}).`+(t.source?" Source-scoped: traffic from other sources is not affected by it.":"")+s}
          ><span class="dot"></span>${t.action}${e.address?"":" (by port)"}</span
        >
      </td>
    `}_renderPortsByBindAddress(e){const t=new Map;for(const s of e){const e=s.address??"__unresolved__",i=t.get(e);i?i.push(s):t.set(e,[s])}const s=Array.from(t.entries()).sort((e,t)=>{const s=St("__unresolved__"===e[0]?null:e[0]),i=St("__unresolved__"===t[0]?null:t[0]);return s.priority!==i.priority?s.priority-i.priority:e[0].localeCompare(t[0])}),i=!!this._firewall?.known_rules?.length,r=this._isOwner,n=3+(i?1:0)+(r?1:0);return K`
      <table>
        <thead>
          <tr>
            ${Qe("Port","port",this._portSort,e=>this._portSort=e)}
            ${Qe("Protocol","proto",this._portSort,e=>this._portSort=e)}
            ${Qe("Interface","interface",this._portSort,e=>this._portSort=e)}
            ${i?K`<th>Covered by rule</th>`:j}
            ${r?K`<th></th>`:j}
          </tr>
        </thead>
        ${s.map(([e,t])=>{const s="__unresolved__"===e?null:e,o=St(s);return K`
            <tbody>
              <tr>
                <td colspan=${n} style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
                  <strong>${s??"unresolved (IPv6)"}</strong>
                  <span class="pill ${o.cls}" style="margin-left:8px;"
                    ><span class="dot"></span>${o.label}</span
                  >
                  <span class="muted" style="margin-left:8px;font-size:12px;"
                    >${t.length} port${1===t.length?"":"s"}</span
                  >
                </td>
              </tr>
              ${(this._portSort?Ze(t,this._portSort,rt.PORT_SORT):t.slice().sort((e,t)=>e.port-t.port)).map(e=>K`
                    <tr>
                      <td>${e.port}</td>
                      <td>${e.proto}</td>
                      <td>
                        ${"(all interfaces)"===e.interface?K`<span class="pill high"><span class="dot"></span>all interfaces</span>`:K`<span class="muted">${e.interface??"—"}</span>`}
                      </td>
                      ${i?this._renderPortRuleCell(e):j}
                      ${r?K`<td>
                            <button
                              class="ha-btn"
                              title="Add firewall rule for this port"
                              @click=${()=>this._onAddFirewallRuleForPort(e)}
                            >
                              Add firewall rule
                            </button>
                          </td>`:j}
                    </tr>
                  `)}
            </tbody>
          `})}
      </table>
    `}_renderRuleCells(e){const t=vt(e);return K`
      <td>
        <span class="pill ${mt(e.action)}"><span class="dot"></span>${e.action}</span>
      </td>
      <td class="mono">${gt(e)}</td>
      <td class="muted">${e.source??"any"}</td>
      <td class="muted">${e.destination??"any"}</td>
      <td class="muted">${e.interface??"any"}</td>
      <td class="muted">${t||"—"}</td>
      ${this._renderFamilyCell(e)}
    `}_fwCapable(e){return!1!==this._firewall?.capabilities?.[e]}_fwMissingCapabilities(){const e=this._firewall?.capabilities;return e?Object.keys(e).filter(t=>!1===e[t]):[]}_fwInterfaceChoices(){const e=new Set(this._probe?.result?.interfaces??[]);for(const t of this._probe?.result?.open_ports??[])t.interface&&"(all interfaces)"!==t.interface&&"unresolved"!==t.interface&&e.add(t.interface);return Array.from(e).sort()}_fwPortChoices(){const e=new Map,t=(this._probe?.result?.open_ports??[]).slice().sort((e,t)=>("0.0.0.0"===e.address?0:1)-("0.0.0.0"===t.address?0:1)||e.port-t.port);for(const s of t){const t=String(s.port);if(e.has(t))continue;const i=[s.proto,s.process??void 0,"(all interfaces)"===s.interface?"all interfaces":s.interface??void 0];e.set(t,`${s.port} — listening: ${i.filter(Boolean).join(", ")}`)}for(const[t,s]of ft){const i=String(t);e.has(i)||e.set(i,`${t} — ${s} (not listening)`)}return Array.from(e.entries()).map(([e,t])=>({value:e,label:t}))}_renderFamilyCell(e){return K`
      <td>
        ${dt(e.family)}
        ${e.partially_applied?K`<span
              class="pill high"
              style="margin-left:6px;"
              title="The host kernel does not support ip6tables, so the IPv6 half of this rule is not applied. Only its IPv4 half (if any) is live."
              ><span class="dot"></span>IPv6 not applied</span
            >`:j}
      </td>
    `}_renderLastOutcomeReason(e){const t=e.history.length?e.history[e.history.length-1]:null;return t?.reason?K`
      <p style="color:var(--error-color,#db4437);font-size:12.5px;margin:8px 0 0;">
        Last test (${t.test_id.slice(0,8)}) ended ${t.status}: ${t.reason}
      </p>
    `:j}_renderFirewallCard(){const e=this._probe,t=this._firewall;return e?.supervisor&&e?.installed?this._isOwner?t?K`
      <div class="card" id="fw-rules-card">
        <h3>Firewall Rules</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Reads, and — if you propose a change — writes the host's firewall via the HA
          SOC Probe add-on's <code>NET_ADMIN</code> capability. Every proposed change is
          backed up first and applied to a dedicated chain this project owns outright,
          never the host's raw INPUT chain. An unconfirmed change reverts itself
          automatically once its test window closes. Rules are dual-stack by default:
          a rule with no source applies to IPv4 and IPv6 alike, and a source address
          pins the rule to that address's own family.
        </p>
        ${!1===t.ipv6_supported?K`
              <p
                style="color:var(--error-color,#db4437);font-size:12.5px;border:1px solid var(--error-color,#db4437);border-radius:4px;padding:8px 10px;"
              >
                IPv6 rules not applied: the host kernel does not support ip6tables.
                Rules with family IPv6 are not live at all, and dual-stack rules are
                live for IPv4 only.
              </p>
            `:j}

        <h4 class="fw-subhead">Active rules</h4>
        ${t.known_rules&&t.known_rules.length?K`
              <table>
                <thead>
                  <tr>
                    ${Qe("Action","action",this._fwRulesSort,e=>this._fwRulesSort=e)}
                    ${Qe("Match","match",this._fwRulesSort,e=>this._fwRulesSort=e)}
                    ${Qe("Source","source",this._fwRulesSort,e=>this._fwRulesSort=e)}
                    ${Qe("Destination","destination",this._fwRulesSort,e=>this._fwRulesSort=e)}
                    ${Qe("Interface","interface",this._fwRulesSort,e=>this._fwRulesSort=e)}
                    ${Qe("Options","options",this._fwRulesSort,e=>this._fwRulesSort=e)}
                    ${Qe("Family","family",this._fwRulesSort,e=>this._fwRulesSort=e)}
                  </tr>
                </thead>
                <tbody>
                  ${Ze(t.known_rules,this._fwRulesSort,rt.FW_RULE_SORT).map(e=>K`<tr>${this._renderRuleCells(e)}</tr>`)}
                </tbody>
              </table>
            `:K`<div class="empty">
              No rules reported yet${null===t.known_rules?" — waiting for the add-on's first report.":"."}
            </div>`}
        ${t.known_rules_reported_at?K`<p class="muted" style="font-size:11.5px;margin:6px 0 0;">
              Last reported ${new Date(t.known_rules_reported_at).toLocaleString()}
            </p>`:j}
        ${this._renderLastOutcomeReason(t)}
        ${t.pending?K`
              ${this._renderFirewallPending(t.pending)}
              ${this._renderFirewallBuilder("A proposed change is still pending. A new test can only be proposed once the add-on has reported the outcome of the current one.")}
            `:this._renderFirewallBuilder(null)}
        ${this._fwError?K`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">${this._fwError}</p>`:j}
      </div>
    `:j:K`
        <div class="card">
          <h3>Firewall Rules <span class="tag cosmetic">owner only</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The firewall is available to the account owner only.
          </p>
        </div>
      `:j}_renderNetscanCard(){const e=this._probe;if(!e?.supervisor||!e?.installed)return j;if(!this._isOwner)return K`
        <div class="card">
          <h3>Network Scan <span class="tag cosmetic">owner only</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The network scan is available to the account owner only.
          </p>
        </div>
      `;const t=this._netscan;if(!t)return j;const s=t.result,i=!!s&&!0===s.capabilities?.tcp_connect;return K`
      <div class="card">
        <h3>
          Network Scan
          <span class="tag ${t.enabled?"enforced":"cosmetic"}">
            ${t.enabled?"enabled":"disabled"}
          </span>
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Local-subnet TCP-connect discovery from the HA SOC Probe add-on: which hosts answer
          on the configured ports, a best-effort banner or TLS certificate read, and a MAC
          vendor label from the host's own ARP table. Stdlib-only on the Probe — no raw
          sockets, no ICMP. Configure the port list and enable it under Settings.
        </p>
        ${t.enabled?s?i?K`
                  <p class="muted" style="font-size:12px;">
                    Last reported ${new Date(s.reported_at).toLocaleString()}
                    ${s.scanner_version?K`(${s.scanner_version})`:j}
                  </p>
                  ${s.hosts.length?this._renderNetscanHostsTable(s.hosts):K`<div class="empty">No hosts discovered.</div>`}
                `:K`
                  <div class="empty">
                    This Probe build hasn't reported netscan capability yet; update the HA SOC
                    Probe add-on to use this feature.
                  </div>
                `:K`<div class="empty">No scan reported yet.</div>`:K`<div class="empty">Netscan is disabled; enable it under Settings to start scanning.</div>`}
        <div class="toolbar" style="margin-top:12px;">
          <button
            class="ha-btn"
            ?disabled=${this._netscanRescanSubmitting||!t.enabled}
            title=${t.enabled?"Ask the Probe to run a scan on its next poll, ahead of its normal schedule.":"Enable netscan under Settings first."}
            @click=${this._onNetscanRescan}
          >
            Rescan now
          </button>
        </div>
        ${this._netscanError?K`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">${this._netscanError}</p>`:j}
      </div>
    `}_renderNetscanPortsCell(e){return e&&e.length?K`
      <td>
        ${e.map(e=>K`
            <div style="margin-bottom:2px;">
              <span class="pill high"><span class="dot"></span>${e.port}</span>
              ${e.service_guess?K`<span class="muted">${e.service_guess}</span>`:j}
              ${e.banner?K`<span class="mono muted" title=${e.banner}> — ${e.banner.slice(0,40)}</span>`:j}
              ${e.tls?K`<span
                    class="pill ${e.tls.self_signed?"medium":"low"}"
                    title=${[e.tls.subject&&`subject: ${e.tls.subject}`,e.tls.issuer&&`issuer: ${e.tls.issuer}`,e.tls.not_after&&`expires: ${e.tls.not_after}`].filter(Boolean).join("\n")}
                    ><span class="dot"></span>TLS${e.tls.self_signed?" (self-signed)":""}</span
                  >`:j}
            </div>
          `)}
      </td>
    `:K`<td class="muted">none</td>`}_renderNetscanHostsTable(e){return K`
      <table>
        <thead>
          <tr>
            ${Qe("IP","ip",this._netscanSort,e=>this._netscanSort=e)}
            ${Qe("MAC","mac",this._netscanSort,e=>this._netscanSort=e)}
            ${Qe("Vendor","vendor",this._netscanSort,e=>this._netscanSort=e)}
            ${Qe("Open ports","open_ports",this._netscanSort,e=>this._netscanSort=e)}
          </tr>
        </thead>
        <tbody>
          ${Ze(e,this._netscanSort,rt.NETSCAN_HOST_SORT).map(e=>K`
              <tr>
                <td class="mono">${e.ip}</td>
                <td class="mono muted">${e.mac??"—"}</td>
                <td class="muted">${e.vendor??"—"}</td>
                ${this._renderNetscanPortsCell(e.open_ports)}
              </tr>
            `)}
        </tbody>
      </table>
    `}_renderFirewallPending(e){const t=Math.max(0,Math.round((new Date(e.expires_at).getTime()-Date.now())/1e3)),s=Date.now()>=new Date(e.expires_at).getTime(),i={testing:e.applied_at?"Testing — live on the host":"Queued — waiting for the add-on to apply",confirmed:"Confirmed — waiting for the add-on to acknowledge",reverted:"Reverting — waiting for the add-on to acknowledge",expired_unreported:"Window expired, the add-on has not confirmed the revert yet",expired:"Window expired, the add-on has not confirmed the revert yet"};return K`
      <h4 class="fw-subhead">Proposed rules — ${i[e.status]??e.status}</h4>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Match</th>
            <th>Source</th>
            <th>Destination</th>
            <th>Interface</th>
            <th>Options</th>
            <th>Family</th>
          </tr>
        </thead>
        <tbody>
          ${e.proposed_rules.map(e=>K`<tr>${this._renderRuleCells(e)}</tr>`)}
        </tbody>
      </table>
      <div class="toolbar" style="margin-top:12px;">
        <button
          class="ha-btn"
          ?disabled=${this._fwSubmitting||"testing"!==e.status}
          @click=${this._onConfirmTest}
        >
          Apply${"testing"===e.status?K` (${t}s to auto-revert)`:j}
        </button>
        <button
          class="ha-btn danger"
          ?disabled=${this._fwSubmitting||"testing"!==e.status}
          @click=${this._onCancelTest}
        >
          Cancel now
        </button>
        ${s?K`
              <button
                class="ha-btn danger"
                ?disabled=${this._fwSubmitting}
                title="The add-on never reported this test's outcome. Discard archives it as 'discarded_unreported' so a new test can be proposed; nothing on the host is changed."
                @click=${this._onDiscardPending}
              >
                Discard unreported test
              </button>
            `:j}
      </div>
    `}_renderFirewallBuilder(e){const t=null===e&&this._fwBackupAck&&this._fwDraftRules.length>0&&this._fwDraftRules.every(e=>this._fwRuleValid(e)),s=this._fwPortChoices(),i=this._fwInterfaceChoices(),r=this._fwMissingCapabilities();return K`
      <h4 class="fw-subhead">Propose a change</h4>
      <p class="muted" style="font-size:12px;margin:0 0 8px;">
        Ports take one number, a range (<code>8000:8100</code>), or a comma list (<code>80,443</code>).
        Rules match inbound traffic to this host only. An address pins the family; a rule with no
        address is dual-stack.
        ${r.length?K`<span style="display:block;margin-top:4px;color:var(--warning-color,#ffa600);"
              >This host's iptables lacks: ${r.join(", ")}. Options needing them are disabled.</span
            >`:j}
      </p>
      <datalist id="fw-port-choices">
        ${s.map(e=>K`<option value=${e.value}>${e.label}</option>`)}
      </datalist>
      <datalist id="fw-interface-choices">
        ${i.map(e=>K`<option value=${e}></option>`)}
      </datalist>
      <datalist id="fw-subnet-choices">
        ${this._fwNetworks.map(e=>K`<option value=${e.ip_subnet}>${e.name}${e.name!==e.ip_subnet?` (${e.ip_subnet})`:""}</option>`)}
      </datalist>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Action</th>
              <th>Protocol</th>
              <th>Ports / ICMP type</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Interface</th>
              <th>Log</th>
              <th>Comment</th>
              <th>Family</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${this._fwDraftRules.map((e,t)=>{const s=yt(e.source??"",e.destination??"")??("icmp"===e.proto?bt(e.icmp_type):null),r=s??e.family??"both",n=s=>i=>{const r=i.target.value.trim(),n={...e,[s]:r},o=yt(n.source??"",n.destination??"");this._fwUpdateRule(t,{[s]:r,family:o??"both"})};return K`
                <tr>
                  <td>
                    <select
                      @change=${e=>this._fwUpdateRule(t,{action:e.target.value})}
                    >
                      <option value="allow" ?selected=${"allow"===e.action}>allow</option>
                      <option value="deny" ?selected=${"deny"===e.action}>deny (drop)</option>
                      <option value="reject" ?selected=${"reject"===e.action} ?disabled=${!this._fwCapable("reject")}>
                        reject
                      </option>
                    </select>
                  </td>
                  <td>
                    <select
                      @change=${e=>{const s=e.target.value;this._fwUpdateRule(t,"icmp"===s?{proto:s,ports:"",icmp_type:"any"}:{proto:s,icmp_type:"any"})}}
                    >
                      <option value="tcp" ?selected=${"tcp"===e.proto}>tcp</option>
                      <option value="udp" ?selected=${"udp"===e.proto}>udp</option>
                      <option value="icmp" ?selected=${"icmp"===e.proto} ?disabled=${!this._fwCapable("icmp")}>icmp</option>
                    </select>
                  </td>
                  <td>
                    ${"icmp"===e.proto?K`
                          <select
                            @change=${s=>{const i=s.target.value,r=bt(i);this._fwUpdateRule(t,{icmp_type:i,family:r??yt(e.source??"",e.destination??"")??"both"})}}
                          >
                            ${me.map(([t,s,i])=>K`
                                <option value=${t} ?selected=${(e.icmp_type??"any")===t}>
                                  ${t}${null===s?" (v6 only)":null===i?" (v4 only)":""}
                                </option>
                              `)}
                          </select>
                        `:K`
                          <input
                            type="text"
                            list="fw-port-choices"
                            placeholder="443 or 8000:8100 or 80,443"
                            .value=${e.ports??""}
                            style="width:150px;"
                            title=${this._fwCapable("multiport")?"Pick an observed listener or type a number, range, or list.":"Comma lists are disabled: this host lacks the multiport extension."}
                            @input=${e=>this._fwUpdateRule(t,{ports:e.target.value.trim()})}
                          />
                        `}
                  </td>
                  <td>
                    <input
                      type="text"
                      list="fw-subnet-choices"
                      placeholder="any, e.g. 192.168.10.0/24"
                      .value=${e.source??""}
                      style="width:160px;"
                      title=${this._fwNetworks.length?"Pick a UniFi network or type an address/CIDR.":"Type an address or CIDR."}
                      @input=${n("source")}
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      list="fw-subnet-choices"
                      placeholder="any, e.g. 192.168.10.5"
                      .value=${e.destination??""}
                      style="width:150px;"
                      title="This host's own address the traffic arrives at; useful on a multi-homed host."
                      @input=${n("destination")}
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      list="fw-interface-choices"
                      placeholder="any"
                      .value=${e.interface??""}
                      style="width:110px;"
                      title=${i.length?"Interfaces reported by the Probe; type another name if it is missing.":"The Probe has not reported interfaces yet; type a name."}
                      @input=${e=>this._fwUpdateRule(t,{interface:e.target.value.trim()})}
                    />
                  </td>
                  <td style="text-align:center;">
                    <input
                      type="checkbox"
                      .checked=${!!e.log}
                      ?disabled=${!(this._fwCapable("log")&&this._fwCapable("limit"))}
                      title="Also log matching packets to the host kernel log, rate-limited to 5 per minute, prefixed HA_SOC:<comment>:"
                      @change=${e=>this._fwUpdateRule(t,{log:e.target.checked})}
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      placeholder="optional"
                      maxlength="22"
                      .value=${e.comment??""}
                      style="width:110px;"
                      ?disabled=${!this._fwCapable("comment")}
                      title="Letters, digits, dot, dash, underscore; shows in iptables -S and in the log prefix."
                      @input=${e=>this._fwUpdateRule(t,{comment:e.target.value.trim()})}
                    />
                  </td>
                  <td>
                    <select
                      ?disabled=${null!==s}
                      title=${null!==s?"Locked: an address or ICMP type pins this rule to its own address family.":"IPv4+IPv6 writes the rule into both tables; pick one family to scope it."}
                      @change=${e=>this._fwUpdateRule(t,{family:e.target.value})}
                    >
                      <option value="both" ?selected=${"both"===r}>IPv4+IPv6</option>
                      <option value="4" ?selected=${"4"===r}>IPv4</option>
                      <option value="6" ?selected=${"6"===r}>IPv6</option>
                    </select>
                  </td>
                  <td><button class="ha-btn danger" @click=${()=>this._fwRemoveRule(t)}>Remove</button></td>
                </tr>
              `})}
          </tbody>
        </table>
      </div>
      <div class="toolbar" style="margin-top:8px;">
        <button class="ha-btn" @click=${this._fwAddRule}>+ Add rule</button>
      </div>

      <label style="display:flex;align-items:flex-start;gap:8px;font-size:12.5px;margin-top:12px;cursor:pointer;">
        <input
          type="checkbox"
          style="margin-top:2px;"
          .checked=${this._fwBackupAck}
          @change=${e=>this._fwBackupAck=e.target.checked}
        />
        <span>
          I understand the current ruleset will be backed up before this change is
          applied, and that an unconfirmed change reverts to that backup automatically
          once the test window closes.
        </span>
      </label>

      <div class="toolbar" style="margin-top:12px;">
        <button class="ha-btn" ?disabled=${!t||this._fwSubmitting} @click=${this._onProposeTest}>
          Test
        </button>
      </div>
      ${e?K`<p class="muted" style="font-size:12px;margin:6px 0 0;">${e}</p>`:j}
    `}};var $t;xt.styles=[qe,a`
      .table-wrap {
        overflow-x: auto;
      }
      .mono {
        font-family: var(--ha-font-family-code, monospace);
        font-size: 12px;
      }
    `],xt.MISCONFIG_SORT={check:e=>e.check,severity:e=>at(String(e.severity)),summary:e=>e.summary},xt.COVERAGE_SORT={domain:e=>e.domain,files:e=>e.cov.scanned_files,oversize:e=>e.cov.skipped_oversize,over_cap:e=>e.cov.skipped_over_cap,parse_failures:e=>e.cov.parse_failures,scanned_at:e=>e.cov.scanned_at},xt.SCANNER_SORT={domain:e=>e.domain,pattern:e=>e.pattern,location:e=>`${e.file}:${e.line}`,confidence:e=>lt(ht,e.confidence),cwe:e=>e.cwe},xt.VULN_SORT={cve:e=>e.cve_id,cvss:e=>{if(null==e.cvss)return null;const t=Number(e.cvss);return Number.isNaN(t)?null:t},confidence:e=>lt(ct,e.confidence)},xt.PORT_SORT={port:e=>e.port,proto:e=>e.proto,interface:e=>e.interface},xt.NETSCAN_HOST_SORT={ip:e=>e.ip.split(".").map(e=>e.padStart(3,"0")).join("."),mac:e=>e.mac??null,vendor:e=>e.vendor??null,open_ports:e=>e.open_ports?.length??0},xt.FW_RULE_SORT={action:e=>e.action,match:e=>gt(e),source:e=>e.source??"any",destination:e=>e.destination??"any",interface:e=>e.interface??"any",options:e=>vt(e),family:e=>dt(e.family)},e([pe()],xt.prototype,"_scannerFindings",void 0),e([pe()],xt.prototype,"_coverage",void 0),e([pe()],xt.prototype,"_vulnFindings",void 0),e([pe()],xt.prototype,"_misconfigFindings",void 0),e([pe()],xt.prototype,"_probe",void 0),e([pe()],xt.prototype,"_loading",void 0),e([pe()],xt.prototype,"_error",void 0),e([pe()],xt.prototype,"_scanning",void 0),e([pe()],xt.prototype,"_scanError",void 0),e([pe()],xt.prototype,"_exportNotice",void 0),e([pe()],xt.prototype,"_firewall",void 0),e([pe()],xt.prototype,"_fwDraftRules",void 0),e([pe()],xt.prototype,"_fwBackupAck",void 0),e([pe()],xt.prototype,"_fwSubmitting",void 0),e([pe()],xt.prototype,"_fwError",void 0),e([pe()],xt.prototype,"_isOwner",void 0),e([pe()],xt.prototype,"_fwNetworks",void 0),e([pe()],xt.prototype,"_netscan",void 0),e([pe()],xt.prototype,"_netscanRescanSubmitting",void 0),e([pe()],xt.prototype,"_netscanError",void 0),e([pe()],xt.prototype,"_misconfigSort",void 0),e([pe()],xt.prototype,"_scannerSort",void 0),e([pe()],xt.prototype,"_vulnSort",void 0),e([pe()],xt.prototype,"_portSort",void 0),e([pe()],xt.prototype,"_fwRulesSort",void 0),e([pe()],xt.prototype,"_coverageSort",void 0),e([pe()],xt.prototype,"_netscanSort",void 0),e([pe()],xt.prototype,"_openResolved",void 0),xt=rt=e([he("ha-soc-scanner-view")],xt);const kt={lock:"Locks",siren:"Sirens",valve:"Valves"},Ct=[{key:"available",label:"Available"},{key:"partial",label:"Partial"},{key:"unavailable",label:"Unavailable"},{key:"disabled",label:"Disabled"},{key:"no_entities",label:"No entities"}],Et=["critical","high","medium","low"],Rt={failing:"Failing",credential:"Credential issue",communication:"Communication issue",collection:"Collection issue",errors:"Logging errors",debug_logging:"Debug logging enabled",disabled:"Disabled"},Pt={failing:{label:"Unavailable",colorVar:"var(--status-critical)"},credential:{label:"Unavailable",colorVar:"var(--status-critical)"},communication:{label:"Unavailable",colorVar:"var(--status-critical)"},collection:{label:"Unavailable",colorVar:"var(--status-critical)"},errors:{label:"Warning",colorVar:"var(--status-warning)"},debug_logging:{label:"Warning",colorVar:"var(--status-warning)"},disabled:{label:"Disabled",colorVar:"var(--cat-other)"}},At=Object.fromEntries(Object.keys(Rt).map((e,t)=>[e,t])),Tt={critical:"critical",high:"serious",medium:"warning"};const Dt=[10,20,50,100,"all"],Lt=[10,20,50,100,"all"];let Mt=$t=class extends Je{constructor(){super(...arguments),this._summary=null,this._deviceOverview=null,this._integrationOverview=null,this._peripherals=null,this._security=null,this._detections=[],this._risk={},this._users=[],this._loading=!0,this._error=null,this._deviceSearch="",this._deviceStatusFilter=null,this._deviceSort={key:"risk_score",dir:-1},this._devicePageSize=10,this._integrationSearch="",this._integrationSort=null,this._integrationPageSize=10}get viewId(){return"dashboard"}connectedCallback(){super.connectedCallback(),this._load()}updated(){this.classList.toggle("dark",!!this.hass?.themes?.darkMode)}async _load(){this._loading=!0,this._error=null;try{const[t,s,i,r,n,o,a,l]=await Promise.all([(e=this.hass,we(e,{type:"ha_soc/dashboard/summary"})),De(this.hass),Le(this.hass),Ie(this.hass),Fe(this.hass),$e(this.hass),xe(this.hass),Se(this.hass)]);this._summary=t,this._deviceOverview=s,this._integrationOverview=i,this._peripherals=r,this._security=n,this._detections=o,this._risk=a,this._users=l}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}var e}async _onAck(e){await ke(this.hass,e,"ack"),await this._load()}async _onResolve(e){await ke(this.hass,e,"resolved"),await this._load()}_nameFor(e){return e?this._users.find(t=>t.id===e)?.name??e:"unknown"}_goto(e){fe(this,e)}_onStatusTileClick(e){this._deviceStatusFilter=this._deviceStatusFilter===e?null:e,this.renderRoot.querySelector("#devices-card")?.scrollIntoView({behavior:"smooth",block:"start"})}_sortedFilteredDevices(){const e=this._deviceOverview?.devices??[],t=this._deviceSearch.trim().toLowerCase(),s=e.filter(e=>(!this._deviceStatusFilter||e.status===this._deviceStatusFilter)&&(!t||(e.name.toLowerCase().includes(t)||e.vendor.toLowerCase().includes(t)||e.os.toLowerCase().includes(t))));return Ze(s,this._deviceSort,$t.DEVICE_SORT)}_filteredIntegrations(){const e=this._integrationOverview?.integrations??[],t=this._integrationSearch.trim().toLowerCase();return Ze(t?e.filter(e=>e.title.toLowerCase().includes(t)||e.domain.toLowerCase().includes(t)):e,this._integrationSort,$t.INTEGRATION_SORT)}_postureTrendGeometry(e,t){const s=e.filter(e=>Number.isFinite(e.score)).map(e=>({...e,score:Math.max(0,Math.min(100,e.score))}));s.length||s.push({date:"Current",score:t,grade:this._summary?.posture.grade??"—"}),1===s.length&&s.push({...s[0],date:"Current"});const i=s.map(e=>e.score);let r=Math.max(0,Math.min(...i)-4),n=Math.min(100,Math.max(...i)+4);n<=r&&(r=Math.max(0,r-1),n=Math.min(100,n+1));const o=118,a=s.map((e,t)=>{return`${(e=>12+e/(s.length-1)*536)(t).toFixed(1)},${(i=e.score,o-(i-r)/(n-r)*106).toFixed(1)}`;var i}).join(" "),l=e=>{const t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(e),s=t?new Date(Number(t[1]),Number(t[2])-1,Number(t[3])):new Date(e);return Number.isNaN(s.getTime())?e:s.toLocaleDateString(void 0,{month:"short",day:"numeric"})};return{points:a,area:`12,118 ${a} 548,118`,firstLabel:l(s[0].date),lastLabel:l(s[s.length-1].date),delta:s[s.length-1].score-s[0].score}}_renderReferenceOverview(){const e=this._summary?.posture,t=this._summary,s=this._deviceOverview;if(!e||!t||!s)return j;const i=(e.missing_terms??[]).map(e=>$t.POSTURE_TERM_LABELS[e]??e),r=this._detections.filter(e=>"open"===e.status).sort((e,t)=>new Date(t.last_seen).getTime()-new Date(e.last_seen).getTime()),n=r.filter(e=>"critical"===e.severity||"high"===e.severity).length,o=s.devices.reduce((e,t)=>e+t.severity_counts.critical+t.severity_counts.high,0),a=s.devices.reduce((e,t)=>(e.critical+=t.severity_counts.critical,e.high+=t.severity_counts.high,e.medium+=t.severity_counts.medium,e.low+=t.severity_counts.low,e),{critical:0,high:0,medium:0,low:0}),l=a.critical+a.high+a.medium+a.low,h=[{label:"Critical",color:"var(--status-critical)",value:a.critical},{label:"High",color:"var(--status-serious)",value:a.high},{label:"Medium",color:"var(--status-warning)",value:a.medium},{label:"Low",color:"var(--cat-1)",value:a.low}];let c=0;const d=h.map(e=>{const t=c;return c+=l?e.value/l*100:0,`${e.color} ${t}% ${c}%`}),u=l?`conic-gradient(${d.join(", ")})`:"rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09)",p=Object.values(this._security?.sources_enabled??{}),_=p.filter(Boolean).length,f=p.length,g=e.score>=85?"good":e.score>=70?"warning":"critical",v="good"===g?"var(--status-good)":"warning"===g?"var(--status-warning)":"var(--status-critical)",m="good"===g?"Healthy":"warning"===g?"Needs attention":"At risk",y=this._postureTrendGeometry(t.posture_history,e.score),b=`${y.delta>=0?"+":""}${y.delta.toFixed(0)}`;return K`
      <div class="overview-heading">
        <div>
          <h2 class="section-title">Security overview</h2>
          <p class="section-subtitle">What needs attention now, with operational health kept separate from risk.</p>
        </div>
        <span class="overview-state">${e.provisional?"Provisional posture":"Live protected data"}</span>
      </div>

      <div class="overview-kpis">
        <div class="overview-kpi">
          <span class="overview-kpi-label">Posture score</span>
          <span class="overview-kpi-value">${e.score}</span>
          <span class="overview-kpi-context">Grade ${e.grade}${e.provisional?" · provisional":" · stable"}</span>
        </div>
        <button class="overview-kpi" type="button" @click=${()=>this._goto("audit")}>
          <span class="overview-kpi-label">Open detections</span>
          <span class="overview-kpi-value" style="color:${r.length?"var(--status-critical)":"inherit"}">${r.length}</span>
          <span class="overview-kpi-context">${n} high priority</span>
        </button>
        <button class="overview-kpi" type="button" @click=${()=>this._goto("scanner")}>
          <span class="overview-kpi-label">Critical / high findings</span>
          <span class="overview-kpi-value" style="color:${o?"var(--status-serious)":"inherit"}">${o.toLocaleString()}</span>
          <span class="overview-kpi-context">Across ${s.devices.length.toLocaleString()} assets</span>
        </button>
        <div class="overview-kpi">
          <span class="overview-kpi-label">Telemetry sources</span>
          <span class="overview-kpi-value">${_} / ${f}</span>
          <span class="overview-kpi-context">${f?"Configured source categories":"No source categories configured"}</span>
        </div>
      </div>

      <div class="card device-status-card overview-card">
        <div class="card-head">
          <div>
            <h3>Asset availability</h3>
            <div class="metric-context">Operational condition only—not vulnerability severity</div>
          </div>
        </div>
        <div class="status-tiles">
          ${Ct.map(e=>K`
              <div
                class="status-tile clickable ${e.key} ${this._deviceStatusFilter===e.key?"active":""}"
                title="Filter the devices investigation queue"
                @click=${()=>this._onStatusTileClick(e.key)}
              >
                <div class="label">${e.label}</div>
                <div class="value">${s.status_counts[e.key]??0}</div>
              </div>
            `)}
        </div>
      </div>

      <div class="card posture-visual-card overview-card">
        <div class="card-head">
          <div><h3>Posture</h3><div class="metric-context">Current weighted security posture</div></div>
        </div>
        <div class="posture-ring-wrap">
          <div
            class="posture-ring"
            role="img"
            aria-label="Posture score ${e.score} out of 100"
            style="--posture-angle:${3.6*Math.max(0,Math.min(100,e.score))}deg;--posture-color:${v};"
          >
            <div class="posture-ring-value"><strong>${e.score}</strong><span>of 100</span></div>
          </div>
          <div>
            ${e.provisional?K`<span class="state-pill warning" title="Waiting on: ${i.join(", ")}">Provisional</span>`:K`<span class="state-pill ${g}">${m}</span>`}
            <p class="posture-description">
              ${y.delta<0?"Posture declined over the displayed period. Review the priority queue below.":"No downward posture trend in the displayed period."}
            </p>
          </div>
        </div>
      </div>

      <div class="card overview-card clickable" @click=${()=>this._goto("scanner")} title="View vulnerability findings">
        <div class="card-head">
          <div><h3>Finding severity</h3><div class="metric-context">Current vulnerability findings by severity</div></div>
        </div>
        <div class="donut-layout">
          <div
            class="severity-donut"
            role="img"
            aria-label="${l.toLocaleString()} findings by severity"
            style="background:${u}"
          ><strong>${l.toLocaleString()}</strong></div>
          <div class="compact-legend">
            ${h.map(e=>K`
                <div class="item">
                  <span class="swatch" style="background:${e.color}"></span>${e.label}
                  <strong>${e.value.toLocaleString()}</strong>
                </div>
              `)}
          </div>
        </div>
      </div>

      <div class="card trend-card overview-card">
        <div class="card-head">
          <div><h3>Posture trend</h3><div class="metric-context">${t.posture_history.length?"Thirty-day score history":"History begins after the first completed posture calculation"}</div></div>
          <span class="state-pill ${y.delta>=0?"good":"critical"}">${b}</span>
        </div>
        <svg class="posture-trend" viewBox="0 0 560 142" role="img" aria-label="Posture score trend, ${b} points">
          <line class="grid-line" x1="12" y1="22" x2="548" y2="22"></line>
          <line class="grid-line" x1="12" y1="70" x2="548" y2="70"></line>
          <line class="grid-line" x1="12" y1="118" x2="548" y2="118"></line>
          <polygon class="trend-area" points=${y.area}></polygon>
          <polyline class="trend-line" points=${y.points}></polyline>
          <text x="12" y="138">${y.firstLabel}</text>
          <text x="548" y="138" text-anchor="end">${y.lastLabel}</text>
        </svg>
      </div>

      <div class="card overview-card">
        <div class="card-head">
          <div>
            <h3>Priority queue</h3>
            <div class="metric-context">Protected details; acknowledgement and remediation stay in this console</div>
          </div>
        </div>
        ${r.length?K`
              <div class="priority-table-wrap">
                <table>
                  <thead>
                    <tr><th>Priority</th><th>Finding</th><th>User</th><th>Status</th><th>Last seen</th><th></th></tr>
                  </thead>
                  <tbody>
                    ${r.map(e=>{return K`
                        <tr>
                          <td>
                            <span class="state-pill ${Tt[e.severity]??""}">${t=e.severity,t.charAt(0).toUpperCase()+t.slice(1)}</span>
                          </td>
                          <td>${e.title}</td>
                          <td>${this._nameFor(e.user_id)}</td>
                          <td>Open</td>
                          <td title=${new Date(e.last_seen).toLocaleString()}>${function(e){const t=Date.now()-new Date(e).getTime();if(!Number.isFinite(t))return e;const s=Math.round(t/6e4);if(s<1)return"just now";if(s<60)return`${s} min ago`;const i=Math.round(s/60);if(i<24)return`${i} hr ago`;const r=Math.round(i/24);return`${r} day${1===r?"":"s"} ago`}(e.last_seen)}</td>
                          <td>
                            <span class="priority-actions">
                              <button class="ha-btn" @click=${()=>this._onAck(e.id)}>Ack</button>
                              <button class="ha-btn" @click=${()=>this._onResolve(e.id)}>Resolve</button>
                            </span>
                          </td>
                        </tr>
                      `;var t})}
                  </tbody>
                </table>
              </div>
            `:K`<div class="empty">No open detections. The priority queue is clear.</div>`}
      </div>
    `}_statusDotColor(e){switch(e){case"unavailable":return"var(--status-critical)";case"partial":return"var(--status-warning)";case"disabled":return"var(--cat-other)";case"no_entities":return"var(--primary-color)";default:return"var(--status-good)"}}render(){if(this._loading)return K`<div class="empty">Loading dashboard…</div>`;if(this._error||!this._summary||!this._deviceOverview||!this._integrationOverview)return K`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the dashboard</h3>
          <p style="font-size:13px;">
            ${this._error??"The server returned an incomplete dashboard payload."}
          </p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const e=this._summary;this._deviceOverview;const t=this._integrationOverview,s=this._detections.filter(e=>"open"===e.status),i=e.entity_state_counts??{unavailable:0,unknown:0},r=i.unavailable+i.unknown,n=this._sortedFilteredDevices(),o="all"===this._devicePageSize?n:n.slice(0,this._devicePageSize),a=e=>{this._deviceSort=e},l=e=>{this._integrationSort=e},h=this._filteredIntegrations(),c="all"===this._integrationPageSize?h:h.slice(0,this._integrationPageSize),d=[{key:"critical",color:"var(--status-critical)",value:e.detection_severity_counts.critical??0},{key:"high",color:"var(--status-serious)",value:e.detection_severity_counts.high??0},{key:"medium",color:"var(--status-warning)",value:e.detection_severity_counts.medium??0},{key:"low",color:"var(--status-good)",value:e.detection_severity_counts.low??0}],u=[{id:"posture_security",title:"Posture & Security",hideable:!1,render:()=>this._renderReferenceOverview()},{id:"device_vuln_overview",title:"Device & Vulnerability Overview",render:()=>K`
      <h2 class="section-title">Operational detail</h2>
      <p class="section-subtitle">Entity-state reliability and security-source health behind the overview.</p>
      <div class="row2">
        <div class="card clickable" @click=${()=>this._goto("entity_remap")} title="Fix broken entity references">
          <div class="card-head">
            <div>
              <h3>Entity reliability</h3>
              <div class="metric-context">Failed and unknown entity states</div>
            </div>
            <div class="metric-number">${r.toLocaleString()}</div>
          </div>
          <div class="identity-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));">
            <div class="identity-stat">
              <div class="metric-label">Unavailable</div>
              <div class="value" style="color:var(--status-critical)">${i.unavailable.toLocaleString()}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">Unknown</div>
              <div class="value" style="color:var(--status-warning)">${i.unknown.toLocaleString()}</div>
            </div>
          </div>
        </div>
        ${this._renderSecurityCard()}
      </div>
        `},{id:"users_detections",title:"Users & Detections",render:()=>K`
      <h2 class="section-title">Identity and active detections</h2>
      <p class="section-subtitle">Account protection and the security signals that need review.</p>
      <div class="row2">
        <div class="card clickable" @click=${()=>this._goto("users")} title="View users">
          <div class="card-head">
            <div>
              <h3>Identity protection</h3>
              <div class="metric-context">MFA adoption across eligible accounts</div>
            </div>
            <div class="metric-number">
              ${e.mfa_counts.enabled+e.mfa_counts.disabled>0?`${Math.round(e.mfa_counts.enabled/(e.mfa_counts.enabled+e.mfa_counts.disabled)*100)}%`:"—"}
            </div>
          </div>
          <div class="mfa-track" aria-label="MFA adoption">
            <div
              class="mfa-fill"
              style="width:${e.mfa_counts.enabled+e.mfa_counts.disabled>0?e.mfa_counts.enabled/(e.mfa_counts.enabled+e.mfa_counts.disabled)*100:0}%"
            ></div>
          </div>
          <div class="identity-grid" style="margin-top:14px;">
            <div class="identity-stat">
              <div class="metric-label">Users</div>
              <div class="value">${e.total_users_count}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">High / critical risk</div>
              <div class="value">${(e.risk_band_counts.high??0)+(e.risk_band_counts.critical??0)}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">No MFA</div>
              <div class="value" style="color:var(--status-serious)">${e.mfa_counts.disabled}</div>
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("audit")} title="View audit / detections">
          <div class="card-head">
            <div>
              <h3>Detection coverage</h3>
              <div class="metric-context">${s.length} currently open</div>
            </div>
            <div class="metric-number">${this._detections.length}</div>
          </div>
          <div class="severity-track" aria-label="Detections by severity">
            ${d.map(e=>K`<span style="width:${this._detections.length?e.value/this._detections.length*100:0}%;background:${e.color}"></span>`)}
          </div>
          <div class="compact-legend">
            ${d.map(e=>K`
                <div class="item">
                  <span class="swatch" style="background:${e.color}"></span>${e.key}
                  <strong>${e.value}</strong>
                </div>
              `)}
          </div>
        </div>
        </div>
      </div>

        `},{id:"devices_integrations",title:"Devices & Integrations",render:()=>K`
      <h2 class="section-title">Investigation queues</h2>
      <p class="section-subtitle">The highest-risk devices and integration failures, sorted for triage.</p>
      <div class="row2">
        <div class="card" id="devices-card">
          <div class="card-head">
            <div>
              <h3>Highest-risk devices</h3>
              <div class="metric-context">Select a row to open the Home Assistant device record</div>
            </div>
          </div>
          ${this._deviceStatusFilter?K`
                <div class="filter-chip" @click=${()=>this._deviceStatusFilter=null}>
                  ${Ct.find(e=>e.key===this._deviceStatusFilter)?.label} ✕
                </div>
              `:j}
          <div class="devices-toolbar">
            <input
              type="text"
              placeholder="Search devices…"
              .value=${this._deviceSearch}
              @input=${e=>this._deviceSearch=e.target.value}
            />
          </div>
          ${0===n.length?K`<div class="empty">No devices found.</div>`:K`
                <div style="overflow-x:auto;">
                  <table>
                    <thead>
                      <tr>
                        ${Qe("Health","status",this._deviceSort,a)}
                        ${Qe("Device","name",this._deviceSort,a)}
                        ${Qe("Vendor","vendor",this._deviceSort,a)}
                        ${Qe("Risk Score","risk_score",this._deviceSort,a,{numeric:!0})}
                        ${Qe("Total","total_findings",this._deviceSort,a,{numeric:!0})}
                        ${Qe("Severity","severity",this._deviceSort,a)}
                      </tr>
                    </thead>
                    <tbody>
                      ${o.map(e=>K`
                          <tr
                            class="clickable"
                            title="Open in Home Assistant's Devices page"
                            @click=${()=>ge(`/config/devices/device/${e.device_id}`)}
                          >
                            <td>
                              <span
                                class="health-dot"
                                title=${e.status.replace("_"," ")}
                                aria-label=${e.status.replace("_"," ")}
                                style="background:${this._statusDotColor(e.status)}"
                              ></span>
                            </td>
                            <td>${e.name}</td>
                            <td class="muted">${e.vendor}</td>
                            <td class="num">${e.risk_score.toFixed(1)}</td>
                            <td class="num">${e.total_findings}</td>
                            <td>
                              <span class="sev-cell">
                                ${Et.map(t=>K`
                                    <span>
                                      <span
                                        class="sev-dot"
                                        style="background:${"critical"===t?"var(--status-critical)":"high"===t?"var(--status-serious)":"medium"===t?"var(--status-warning)":"var(--status-good)"}"
                                      ></span
                                      >${e.severity_counts[t]}
                                    </span>
                                  `)}
                              </span>
                            </td>
                          </tr>
                        `)}
                    </tbody>
                  </table>
                </div>
                <div class="devices-footer">
                  <span
                    >Showing ${o.length} of ${n.length} device${1===n.length?"":"s"}</span
                  >
                  <select
                    .value=${String(this._devicePageSize)}
                    @change=${e=>{const t=e.target.value;this._devicePageSize="all"===t?"all":Number(t)}}
                  >
                    ${Dt.map(e=>K`
                        <option value=${String(e)} ?selected=${e===this._devicePageSize}>
                          ${"all"===e?"Show all":`Show ${e}`}
                        </option>
                      `)}
                  </select>
                </div>
              `}
        </div>

        <div class="card">
          <div class="card-head">
            <div>
              <h3>Integration issues</h3>
              <div class="metric-context">Setup, credential, communication, and logging health</div>
            </div>
          </div>
          ${0===t.integrations.length?K`<div class="empty">No integration issues detected.</div>`:K`
                <div class="devices-toolbar">
                  <input
                    type="text"
                    placeholder="Search integrations…"
                    .value=${this._integrationSearch}
                    @input=${e=>this._integrationSearch=e.target.value}
                  />
                </div>
                ${0===h.length?K`<div class="empty">No integration matches "${this._integrationSearch}".</div>`:K`
                      <div style="overflow-x:auto;">
                        <table>
                          <thead>
                            <tr>
                              ${Qe("Integration","title",this._integrationSort,l)}
                              ${Qe("Severity","severity",this._integrationSort,l)}
                            </tr>
                          </thead>
                          <tbody>
                            ${c.map(e=>{const t=Pt[e.issue_category];return K`
                                <tr
                                  class="clickable"
                                  title="${e.title} — ${Rt[e.issue_category]}. Open in Home Assistant's Devices page"
                                  @click=${()=>ge(ve(e.entry_id))}
                                >
                                  <td>${e.title}</td>
                                  <td>
                                    <span class="sev-cell">
                                      <span class="sev-dot" style="background:${t.colorVar}"></span>
                                      ${t.label}
                                      ${e.error_count_24h?K`<span class="num">${e.error_count_24h} error${1===e.error_count_24h?"":"s"}</span>`:j}
                                    </span>
                                  </td>
                                </tr>
                              `})}
                          </tbody>
                        </table>
                      </div>
                      <div class="devices-footer">
                        <span
                          >Showing ${c.length} of ${h.length} integration${1===h.length?"":"s"}</span
                        >
                        <select
                          .value=${String(this._integrationPageSize)}
                          @change=${e=>{const t=e.target.value;this._integrationPageSize="all"===t?"all":Number(t)}}
                        >
                          ${Lt.map(e=>K`
                              <option value=${String(e)} ?selected=${e===this._integrationPageSize}>
                                ${"all"===e?"Show all":`Show ${e}`}
                              </option>
                            `)}
                        </select>
                      </div>
                    `}
              `}
        </div>
      </div>
        `}];return this._renderSections(u)}_renderSecurityCard(){const e=this._security;if(!e)return j;const t={};for(const s of e.entities)(t[s.domain]??=[]).push(s);return K`
      <div class="card">
        <div class="card-head">
          <div>
            <h3>Security-source health</h3>
            <div class="metric-context">Locks, sirens, valves, and local peripherals</div>
          </div>
          ${e.problem_count||e.low_battery_count?K`<span class="state-pill critical">
                ${e.problem_count} problem${1===e.problem_count?"":"s"} · ${e.low_battery_count} low battery
              </span>`:K`<span class="state-pill good">All clear</span>`}
        </div>
        <div class="security-health-grid">
          ${Object.entries(kt).filter(([t])=>e.sources_enabled[t]??!0).map(([e,s])=>{const i=t[e]??[],r=i.filter(e=>e.problem),n=r.length,o=i.filter(e=>e.low_battery).length,a=r.slice(0,8).map(e=>`${e.entity_id}: ${e.reason??e.state??"problem"}`);n>8&&a.push(`and ${n-8} more`);const l=i.length?[`View ${s.toLowerCase()} in Home Assistant's Devices page`,...a].join("\n"):"";return K`
                <div
                  class="security-source-tile ${i.length?"clickable":""}"
                  title=${l}
                  @click=${()=>i.length&&ge(function(e){return`/config/devices/dashboard?historyBack=1&domain=${e}`}(e))}
                >
                  <div class="label">${s}</div>
                  <div class="value" style="color:${n?"var(--error-color,#db4437)":"inherit"}">
                    ${n}
                  </div>
                  <div class="sub">
                    ${i.length} total${o?`, ${o} low battery`:""}
                  </div>
                </div>
              `})}
          ${this._renderPeripheralsTile()}
        </div>
      </div>
    `}_renderPeripheralsTile(){const e=this._peripherals;return e&&e.available?K`
      <div
        class="security-source-tile clickable"
        title="View Local Peripherals"
        @click=${()=>this._goto("peripherals")}
      >
        <div class="label">Local Peripherals</div>
        <div class="value" style="color:${e.unassigned_count?"var(--status-warning)":"inherit"}">
          ${e.total_count?e.unassigned_count:0}
        </div>
        <div class="sub">
          ${e.total_count?`${e.total_count} total`:"no USB serial devices detected"}
        </div>
      </div>
    `:j}};var Bt;Mt.styles=[qe,a`
      h2.section-title {
        font-size: 18px;
        letter-spacing: -0.01em;
        color: var(--primary-text-color);
        margin: 30px 0 4px;
        font-weight: 650;
      }
      h2.section-title:first-child {
        margin-top: 0;
      }

      .row3 {
        display: grid;
        grid-template-columns: minmax(320px, 1.35fr) repeat(3, minmax(190px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .row2 {
        display: grid;
        grid-template-columns: minmax(0, 1.65fr) minmax(300px, 1fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      .donuts-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      @container (max-width: 900px) {
        .row3,
        .row2,
        .donuts-row {
          grid-template-columns: 1fr;
        }
      }

      .clickable {
        cursor: pointer;
        transition: transform 0.08s ease, box-shadow 0.08s ease;
      }
      .clickable:hover {
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
        transform: translateY(-1px);
      }

      .section-subtitle {
        color: var(--secondary-text-color);
        font-size: 13px;
        line-height: 1.45;
        margin: 0 0 14px;
      }
      .overview-heading {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 16px;
      }
      .overview-heading .section-subtitle {
        margin-bottom: 0;
      }
      .overview-heading h2.section-title {
        margin-top: 0;
      }
      .overview-state {
        flex: 0 0 auto;
        padding: 6px 11px;
        border: 1px solid var(--soc-border);
        border-radius: 999px;
        color: var(--soc-text-muted);
        background: var(--soc-surface);
        font-size: 11.5px;
        white-space: nowrap;
      }
      .overview-kpis {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 12px;
      }
      .overview-kpi {
        appearance: none;
        min-width: 0;
        padding: 16px 18px 14px;
        border: 1px solid var(--soc-border);
        border-radius: var(--soc-card-radius);
        background: var(--soc-surface);
        color: var(--soc-text);
        font: inherit;
        text-align: left;
        display: flex;
        flex-direction: column;
      }
      .overview-kpi-label {
        color: var(--secondary-text-color);
        font-size: 13px;
        line-height: 1.3;
      }
      button.overview-kpi {
        cursor: pointer;
      }
      button.overview-kpi:hover,
      button.overview-kpi:focus-visible {
        border-color: var(--primary-color);
        outline: none;
      }
      .overview-kpi-value {
        display: block;
        margin: 8px 0 6px;
        font-size: 32px;
        font-weight: 700;
        line-height: 1;
        letter-spacing: -0.02em;
        font-variant-numeric: tabular-nums;
      }
      .overview-kpi-context {
        color: var(--secondary-text-color);
        font-size: 12.5px;
        line-height: 1.35;
      }
      .state-pill {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        line-height: 1.2;
        white-space: nowrap;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.07);
        color: var(--primary-text-color);
      }
      .state-pill.good {
        background: rgba(12, 163, 12, 0.14);
        color: var(--status-good);
      }
      .state-pill.warning {
        background: rgba(250, 178, 25, 0.18);
        color: #9a6700;
      }
      :host(.dark) .state-pill.warning {
        color: var(--status-warning);
      }
      .state-pill.serious {
        background: rgba(236, 131, 90, 0.18);
        color: #b4471c;
      }
      :host(.dark) .state-pill.serious {
        color: var(--status-serious);
      }
      .state-pill.critical {
        background: rgba(208, 59, 59, 0.14);
        color: var(--status-critical);
      }
      .overview-visuals {
        display: grid;
        grid-template-columns: minmax(280px, 0.8fr) minmax(0, 1.7fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      .overview-card {
        margin-bottom: 12px;
      }
      .posture-visual-card,
      .trend-card {
        margin: 0;
      }
      .posture-ring-wrap {
        display: grid;
        grid-template-columns: 132px minmax(0, 1fr);
        align-items: center;
        gap: 16px;
      }
      .posture-ring {
        width: 126px;
        aspect-ratio: 1;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: conic-gradient(
          var(--posture-color) 0 var(--posture-angle),
          rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09) var(--posture-angle) 360deg
        );
        position: relative;
      }
      .posture-ring::before {
        content: "";
        position: absolute;
        inset: 13px;
        border-radius: 50%;
        background: var(--soc-surface);
      }
      .posture-ring-value {
        position: relative;
        z-index: 1;
        text-align: center;
      }
      .posture-ring-value strong {
        display: block;
        font-size: 32px;
        line-height: 1;
      }
      .posture-ring-value span {
        display: block;
        margin-top: 4px;
        color: var(--secondary-text-color);
        font-size: 11px;
      }
      .posture-description {
        color: var(--secondary-text-color);
        font-size: 13px;
        line-height: 1.45;
        margin: 10px 0 0;
      }
      .posture-trend {
        width: 100%;
        height: 142px;
        display: block;
      }
      .posture-trend .grid-line {
        stroke: var(--divider-color);
        stroke-width: 1;
      }
      .posture-trend .trend-area {
        fill: rgba(var(--rgb-primary-color, 3, 155, 229), 0.14);
      }
      .posture-trend .trend-line {
        fill: none;
        stroke: var(--primary-color);
        stroke-width: 3;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      .posture-trend text {
        fill: var(--secondary-text-color);
        font-size: 10px;
      }
      .metric-label {
        color: var(--secondary-text-color);
        font-size: 11px;
        font-weight: 650;
        letter-spacing: 0.055em;
        text-transform: uppercase;
      }
      .severity-track,
      .mfa-track {
        height: 7px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09);
      }
      .mfa-fill {
        height: 100%;
        border-radius: inherit;
        background: var(--primary-color);
      }
      .summary-grid {
        display: grid;
        grid-template-columns: minmax(420px, 1.5fr) repeat(2, minmax(240px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .summary-grid > .card {
        margin: 0;
      }
      .card-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 14px;
      }
      .card-head h3 {
        margin: 0;
      }
      .metric-number {
        font-size: 34px;
        font-weight: 720;
        line-height: 1;
        letter-spacing: -0.025em;
        font-variant-numeric: tabular-nums;
      }
      .metric-context {
        color: var(--secondary-text-color);
        font-size: 12px;
        margin-top: 5px;
      }
      .severity-track {
        display: flex;
        margin: 16px 0 12px;
      }
      .severity-track > span {
        min-width: 2px;
      }
      .compact-legend {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 7px 12px;
        font-size: 12px;
      }
      .compact-legend .item {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .compact-legend .item strong {
        margin-left: auto;
        font-variant-numeric: tabular-nums;
      }
      .compact-legend .swatch {
        width: 8px;
        height: 8px;
        border-radius: 2px;
      }
      .donut-layout {
        display: grid;
        grid-template-columns: 126px minmax(0, 1fr);
        gap: 15px;
        align-items: center;
      }
      .donut-layout .compact-legend {
        grid-template-columns: 1fr;
      }
      .severity-donut {
        width: 126px;
        aspect-ratio: 1;
        border-radius: 50%;
        display: grid;
        place-items: center;
        position: relative;
      }
      .severity-donut::before {
        content: "";
        position: absolute;
        inset: 16px;
        border-radius: 50%;
        background: var(--soc-surface);
      }
      .severity-donut strong {
        position: relative;
        z-index: 1;
        font-size: 28px;
        font-variant-numeric: tabular-nums;
      }
      .identity-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
      }
      .identity-stat {
        border: 1px solid var(--divider-color);
        border-radius: 10px;
        padding: 12px;
      }
      .identity-stat .value {
        font-size: 24px;
        font-weight: 700;
        margin-top: 5px;
      }

      /* -- Status tiles -------------------------------------------------- */
      /* Stretches to fill whatever height row3's tallest sibling card
         (the donut / gauge cards) ends up at, rather than sizing to its
         own short content and leaving dead space below. */
      .device-status-card {
        display: flex;
        flex-direction: column;
      }
      .status-tiles {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        flex: 1;
      }
      .status-tile {
        border-radius: 10px;
        padding: 10px 6px;
        text-align: left;
        background: var(--soc-surface-subtle);
        border: 1px solid transparent;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: center;
        gap: 6px;
      }
      .status-tile.active {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      .status-tile .label {
        font-size: 11.5px;
        font-weight: 600;
        opacity: 0.85;
      }
      .status-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.3;
      }
      .status-tile.available {
        background: rgba(12, 163, 12, 0.11);
        color: var(--status-good);
      }
      .priority-table-wrap {
        overflow-x: auto;
      }
      .priority-table-wrap table {
        min-width: 680px;
      }
      .priority-table-wrap th {
        text-transform: none;
        letter-spacing: 0;
        font-size: 13px;
        font-weight: 600;
      }
      .priority-table-wrap td {
        font-size: 13.5px;
        vertical-align: middle;
      }
      .priority-actions {
        display: flex;
        gap: 6px;
        white-space: nowrap;
      }
      .status-tile.partial {
        background: rgba(250, 178, 25, 0.15);
        color: var(--status-warning);
      }
      .status-tile.unavailable {
        background: rgba(208, 59, 59, 0.12);
        color: var(--status-critical);
      }
      .status-tile.no_entities {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.09);
      }

      .filter-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        background: var(--primary-color);
        color: #fff;
        padding: 4px 10px;
        border-radius: 100px;
        cursor: pointer;
        margin-bottom: 10px;
      }

      /* -- All Devices table --------------------------------------------------- */
      .devices-toolbar {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
      }
      .devices-toolbar input {
        flex: 1;
        font: inherit;
        font-size: 13px;
        padding: 7px 10px;
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
      }
      .health-dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
      }
      .sev-cell {
        display: inline-flex;
        gap: 8px;
        font-variant-numeric: tabular-nums;
        font-size: 11.5px;
      }
      .sev-cell span {
        display: inline-flex;
        align-items: center;
        gap: 3px;
      }
      .sev-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
      }

      /* -- All Devices pagination ------------------------------------------ */
      .devices-footer {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        color: var(--secondary-text-color);
      }
      .devices-footer select {
        margin-left: auto;
      }

      /* -- Security Integrations Health card --------------------------------- */
      .security-health-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 8px;
        margin-top: 8px;
      }
      .security-source-tile {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 9px 11px;
      }
      .security-source-tile .label {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      .security-source-tile .value {
        font-size: 18px;
        font-weight: 700;
      }
      .security-source-tile .sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      @container (max-width: 1100px) {
        .overview-kpis {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .overview-visuals {
          grid-template-columns: 1fr;
        }
      }
      @container (max-width: 900px) {
        .summary-grid,
        .identity-grid {
          grid-template-columns: 1fr;
        }
      }
      @container (max-width: 560px) {
        .overview-heading {
          display: block;
        }
        .overview-state {
          display: inline-flex;
          margin-top: 10px;
        }
        .overview-kpis {
          grid-template-columns: 1fr;
        }
        .posture-ring-wrap,
        .donut-layout {
          grid-template-columns: 1fr;
          justify-items: center;
        }
        .status-tiles {
          grid-template-columns: repeat(2, 1fr);
        }
      }
    `],Mt.DEVICE_SORT={status:e=>Ct.findIndex(t=>t.key===e.status),name:e=>e.name,vendor:e=>e.vendor,risk_score:e=>e.risk_score,total_findings:e=>e.total_findings,severity:e=>1e9*e.severity_counts.critical+1e6*e.severity_counts.high+1e3*e.severity_counts.medium+e.severity_counts.low},Mt.INTEGRATION_SORT={title:e=>e.title,severity:e=>At[e.issue_category]},Mt.POSTURE_TERM_LABELS={p_user:"user risk",p_vuln:"device vulnerabilities",p_misconfig:"misconfigurations",p_integration:"integration health",p_detection:"detections"},e([pe()],Mt.prototype,"_summary",void 0),e([pe()],Mt.prototype,"_deviceOverview",void 0),e([pe()],Mt.prototype,"_integrationOverview",void 0),e([pe()],Mt.prototype,"_peripherals",void 0),e([pe()],Mt.prototype,"_security",void 0),e([pe()],Mt.prototype,"_detections",void 0),e([pe()],Mt.prototype,"_risk",void 0),e([pe()],Mt.prototype,"_users",void 0),e([pe()],Mt.prototype,"_loading",void 0),e([pe()],Mt.prototype,"_error",void 0),e([pe()],Mt.prototype,"_deviceSearch",void 0),e([pe()],Mt.prototype,"_deviceStatusFilter",void 0),e([pe()],Mt.prototype,"_deviceSort",void 0),e([pe()],Mt.prototype,"_devicePageSize",void 0),e([pe()],Mt.prototype,"_integrationSearch",void 0),e([pe()],Mt.prototype,"_integrationSort",void 0),e([pe()],Mt.prototype,"_integrationPageSize",void 0),Mt=$t=e([he("ha-soc-dashboard-view")],Mt);const Ot=[25,50,100,"all"];function zt(e){if(!e)return null;try{const t=new URL(e).protocol;return"http:"===t||"https:"===t?e:null}catch{return null}}let It=Bt=class extends Je{constructor(){super(...arguments),this.initialClientFilter=null,this._overview=null,this._loading=!0,this._error=null,this._clientSearch="",this._clientPage=0,this._clientPageSize=25,this._clientVlanFilter="",this._clientSsidFilter="",this._clientSort=null,this._wifiSsidFilter=null,this._deviceSearch="",this._devicePage=0,this._devicePageSize=25,this._deviceSort=null,this._protectSort=null,this._eventSort=null}get viewId(){return"network"}connectedCallback(){super.connectedCallback(),this._load()}updated(e){super.updated(e),e.has("initialClientFilter")&&this.initialClientFilter&&(this._clientSearch=this.initialClientFilter,this._clientPage=0,this.dispatchEvent(new CustomEvent("client-filter-consumed")))}async _load(){this._loading=!0,this._error=null;try{this._overview=await He(this.hass)}catch(e){this._error=e instanceof Error?e.message:String(e),this._overview=null}finally{this._loading=!1}}_fmtBytes(e){if(null==e)return"—";if(e<1024)return`${e} B`;const t=["KB","MB","GB","TB","PB"];let s=e/1024,i=0;for(;s>=1024&&i<t.length-1;)s/=1024,i++;return`${s.toFixed(s>=100?0:1)} ${t[i]}`}_fmtRate(e){if(null==e)return"—";const t=8*e;if(t<1e3)return`${t} bps`;const s=["kbps","Mbps","Gbps"];let i=t/1e3,r=0;for(;i>=1e3&&r<s.length-1;)i/=1e3,r++;return`${i.toFixed(i>=100?0:1)} ${s[r]}`}_fmtBandwidth(e){return e?`↓ ${this._fmtBytes(e.rx_bytes)} · ↑ ${this._fmtBytes(e.tx_bytes)}`:"—"}_fmtUptime(e){if(null==e)return"—";const t=Math.floor(e/86400),s=Math.floor(e%86400/3600),i=Math.floor(e%3600/60);return t>0?`${t}d ${s}h`:s>0?`${s}h ${i}m`:`${i}m`}_fmtLastSeen(e){if(null==e)return"—";const t=Date.now()/1e3,s=Math.max(0,t-e);return s<60?"just now":s<3600?`${Math.floor(s/60)}m ago`:s<86400?`${Math.floor(s/3600)}h ago`:s<2592e3?`${Math.floor(s/86400)}d ago`:new Date(1e3*e).toLocaleDateString()}_fmtVlan(e){return null==e||""===e?"—":String(e)}_renderMatch(e){const t=e.integration_match;if(!t)return K`<span class="muted">—</span>`;const s=t.failing?"failing":t.healthy?"healthy":"other",i=t.failing?"⚠":t.healthy?"●":"○",r=`${t.domain} — config entry state: ${t.state}. Click to open in Home Assistant.`;return K`
      <span
        class="match ${s}"
        title=${r}
        @click=${()=>ge(ve(t.entry_id))}
      >
        ${i} ${t.domain}${t.failing?" failing":""}
      </span>
    `}_filter(e,t){const s=t.trim().toLowerCase();return s?e.filter(e=>[e.name,e.ipv4,e.ipv6,e.mac,e.ssid,e.integration_match?.domain].filter(Boolean).some(e=>String(e).toLowerCase().includes(s))):e}_paginate(e,t,s){return"all"===s?e:e.slice(t*s,t*s+s)}render(){if(this._loading)return K`<div class="empty">Loading network…</div>`;if(this._error)return K`<div class="alert">Could not load the Network overview: ${this._error}</div>`;const e=this._overview;if(!e)return K`<div class="empty">No network data.</div>`;if(!e.configured)return K`
        <div class="card">
          <h3>UniFi Network not configured</h3>
          <p class="muted" style="font-size:13px;line-height:1.6;">
            Add a UniFi Network controller host and a local API key in
            <strong>Settings</strong> (owner only) to see status, WAN throughput,
            wireless clients, and the client / device tables here. The API key is a
            local one generated on the console under
            <em>Settings → Control Plane → Integrations</em>; nothing leaves your LAN.
          </p>
          <button class="ha-btn" @click=${()=>fe(this,"settings")}>
            Open Settings
          </button>
        </div>
        ${this._renderProtectCard(e)}
      `;if(!e.reachable)return K`
        <div class="alert">
          <strong>UniFi Network is configured but not reachable.</strong><br />
          ${e.error??"Unknown error."}
        </div>
        <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        ${this._renderProtectCard(e)}
      `;const t=[{id:"overview",title:"Status & Wireless Overview",hideable:!1,render:()=>K`${this._renderFailingBanner(e)} ${this._renderStats(e)} ${this._renderSsid(e)}`},{id:"clients",title:"Clients",render:()=>this._renderClientsTable(e)},{id:"devices",title:"Network Devices",render:()=>this._renderDevicesTable(e)},{id:"wifi-join",title:"Wi-Fi Join Diagnostics",render:()=>this._renderWifiJoin(e)},{id:"protect",title:"UniFi Protect",render:()=>this._renderProtectCard(e)}];return K`
      ${this._renderSections(t)}
      <div class="footer">
        <span>Last updated ${new Date(e.generated_at).toLocaleTimeString()}</span>
        <button class="ha-btn" style="margin-left:auto;" @click=${()=>this._load()}>
          Refresh
        </button>
      </div>
    `}_renderFailingBanner(e){return e.failing_endpoint_count?K`
      <div class="alert">
        <strong>⚠ ${e.failing_endpoint_count} Home Assistant integration${1===e.failing_endpoint_count?"":"s"} with a failing config entry ${1===e.failing_endpoint_count?"is":"are"} still present on the network.</strong>
        An integration whose device is online (a live client below) but whose config
        entry is in a setup-error/retry state is exactly the "an integration IP is
        failing" case — the device is reachable, so the fault is the integration, not
        the network. Look for the red <span class="match failing" style="cursor:default;"
        >⚠ failing</span> tags in the Integration column.
      </div>
    `:j}_renderStats(e){const t="online"===e.status,s=e.internet_connected;return K`
      <div class="stat-row">
        <div class="stat-tile">
          <div class="label">Network Status</div>
          <div class="value">
            <span class="dot ${t?"good":"bad"}"></span>${t?"Online":"Offline"}
          </div>
          <div class="sub">${e.site_id?`site ${e.site_id}`:""}</div>
        </div>
        <div class="stat-tile">
          <div class="label">Internet</div>
          <div class="value">
            <span class="dot ${!0===s?"good":!1===s?"bad":"unknown"}"></span>${!0===s?"Connected":!1===s?"Down":"Unknown"}
          </div>
          <div class="sub">${e.wan.ip?`WAN ${e.wan.ip}`:e.wan.port?e.wan.port:"—"}</div>
        </div>
        <div class="stat-tile">
          <div class="label">WAN Bandwidth</div>
          <div class="value" style="font-size:18px;">
            ↓ ${this._fmtRate(e.wan.rx_rate_bps)}
          </div>
          <div class="sub">↑ ${this._fmtRate(e.wan.tx_rate_bps)}${e.wan.port?` · ${e.wan.port}`:""}</div>
        </div>
        <div class="stat-tile">
          <div class="label">Wireless Clients</div>
          <div class="value">${e.wireless_client_count}</div>
          <div class="sub">${e.wired_client_count} wired</div>
        </div>
        <div class="stat-tile">
          <div class="label">Total Clients</div>
          <div class="value">${e.total_client_count}</div>
          <div class="sub">${e.devices.length} network devices</div>
        </div>
      </div>
    `}_selectSsid(e){this._clientSsidFilter=this._clientSsidFilter===e?"":e,this._clientPage=0,this._clientSsidFilter&&this.updateComplete.then(()=>{this.renderRoot?.querySelector("#clients-card")?.scrollIntoView({behavior:"smooth",block:"start"})})}_renderFinding(e){return K`
      <li class="finding ${e.severity}">
        <span class="sev">${e.severity}</span>
        <span>${e.message}</span>
      </li>
    `}_apScopeText(e){const t=e.ap_scope;if("ALL"===t.type)return"Every access point";if("DEVICE_TAGS"===t.type)return`${t.tag_count} device tags (not resolvable)`;const s=t.device_names.join(", "),i=t.unresolved?` + ${t.unresolved} unlisted`:"";return s?`${s}${i}`:`${t.unresolved} unlisted access points`}_renderSsidReadiness(e,t){const s=new Set(e.clients.filter(e=>!e.wired&&e.ssid===t.ssid&&e.ap).map(e=>e.ap)),i=t.frequencies.length?t.frequencies.map(e=>`${e} GHz`).join(", "):"—";return K`
      <div class="wifi-ssid">
        <div class="wifi-head">
          <strong>${t.ssid}</strong>
          <span class="pill ${!1===t.enabled?"bad":"ok"}">
            ${!1===t.enabled?"disabled":"enabled"}
          </span>
          ${"IOT_OPTIMIZED"===t.kind?K`<span class="pill">IoT optimised</span>`:j}
          ${t.security?K`<span class="pill">${t.security}</span>`:j}
        </div>
        <div class="wifi-grid">
          <div><span class="muted">Network</span> ${t.network??"—"}</div>
          <div><span class="muted">Radios</span> ${i}</div>
          <div><span class="muted">Permitted APs</span> ${this._apScopeText(t)}</div>
          <div>
            <span class="muted">Carrying clients now</span>
            ${s.size?[...s].sort().join(", "):"none"}
          </div>
        </div>
        ${t.findings.length?K`<ul class="findings">
              ${t.findings.map(e=>this._renderFinding(e))}
            </ul>`:K`<p class="muted" style="margin:6px 0 0;">
              Nothing in this SSID's configuration refuses a client.
            </p>`}
      </div>
    `}_renderWifiJoin(e){const t=e.wifi_join,s=this._wifiSsidFilter??(t.ssids.find(e=>e.likely_iot)?.ssid||""),i=s?t.ssids.filter(e=>e.ssid===s):t.ssids;return K`
      <div class="card" id="wifi-join-card">
        <h3>Wi-Fi Join Diagnostics</h3>
        <p class="muted" style="margin-top:0;">
          No UniFi source records an association attempt or an authentication failure, so nothing
          here says a client failed. What it shows is the configuration that decides whether a join
          is permitted, which access points carry each SSID, and the wireless clients the
          controller knows but is not carrying now.
        </p>
        ${t.available?K`
              <div class="wifi-filter">
                <label class="muted">SSID</label>
                <select
                  .value=${s}
                  @change=${e=>{this._wifiSsidFilter=e.target.value}}
                >
                  <option value="">All SSIDs</option>
                  ${t.ssids.map(e=>K`<option value=${e.ssid}>${e.ssid}</option>`)}
                </select>
              </div>
              ${i.map(t=>this._renderSsidReadiness(e,t))}
            `:K`<div class="alert">
              The console did not return its Wi-Fi broadcasts, so no SSID configuration can be
              read. The list below still applies.
            </div>`}
        <h4>Known but not connected</h4>
        ${t.absent_available?t.absent_clients.length?K`
                <table>
                  <thead>
                    <tr>
                      <th>Client</th>
                      <th>MAC</th>
                      <th>Last SSID</th>
                      <th>Last seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${t.absent_clients.map(e=>K`
                        <tr>
                          <td>${e.name}</td>
                          <td class="mono">${e.mac}</td>
                          <td>${e.ssid??"—"}</td>
                          <td>${this._fmtLastSeen(e.last_seen)}</td>
                        </tr>
                      `)}
                  </tbody>
                </table>
              `:K`<p class="muted">
                Every wireless client the controller knows is connected right now.
              </p>`:K`<p class="muted">
              This list comes from the core UniFi integration's all-clients collection, which is not
              loaded. A client that has never associated appears in no collection at all, so its
              absence here is not evidence that it is fine.
            </p>`}
      </div>
    `}_renderSsid(e){if(!e.clients_per_ssid.length)return j;const t=Math.max(...e.clients_per_ssid.map(e=>e.count),1);return K`
      <div class="card">
        <h3>Clients per SSID <span class="muted" style="font-weight:400;font-size:12px;">— click to filter the table</span></h3>
        <div class="ssid-list">
          ${e.clients_per_ssid.map(e=>K`
              <div
                class="ssid-row clickable ${this._clientSsidFilter===e.ssid?"active":""}"
                @click=${()=>this._selectSsid(e.ssid)}
                title="Filter Clients to ${e.ssid}"
              >
                <span class="name">${e.ssid}</span>
                <span class="bar"><span style="width:${e.count/t*100}%"></span></span>
                <span class="count">${e.count}</span>
              </div>
            `)}
        </div>
      </div>
    `}_colHeaders(){const e=this._clientSort,t=e=>{this._clientSort=e,this._clientPage=0};return K`
      <tr>
        ${Qe("Client","name",e,t)}
        ${Qe("IPv4","ipv4",e,t)}
        ${Qe("IPv6","ipv6",e,t)}
        ${Qe("MAC","mac",e,t)}
        ${Qe("VLAN","vlan",e,t,{numeric:!0})}
        ${Qe("SSID","ssid",e,t)}
        ${Qe("Uptime","uptime",e,t,{numeric:!0})}
        ${Qe("Bandwidth","bandwidth",e,t)}
        ${Qe("Last Seen","last_seen",e,t)}
        ${Qe("Integration","integration",e,t)}
      </tr>
    `}_renderRow(e,t={}){const s=e;return K`
      <tr>
        <td>
          <div style="font-weight:600;">${e.name}</div>
          ${t.model||e.wired?t.model&&s.state?K`<div class="muted" style="font-size:11px;">${s.state.toLowerCase()}</div>`:j:K`<div class="muted" style="font-size:11px;">wireless</div>`}
        </td>
        <td class="mono">${e.ipv4??"—"}</td>
        <td class="mono">${e.ipv6??"—"}</td>
        <td class="mono">${e.mac??"—"}</td>
        <td class="num">${this._fmtVlan(e.vlan)}</td>
        <td>${e.ssid??(e.wired?K`<span class="muted">wired</span>`:"—")}</td>
        ${t.model?K`<td>${s.model??"—"}</td>`:j}
        <td class="num">${this._fmtUptime(e.uptime)}</td>
        <td>${this._fmtBandwidth(e.bandwidth)}</td>
        <td>${this._fmtLastSeen(e.last_seen)}</td>
        <td>${this._renderMatch(e)}</td>
      </tr>
    `}_renderClientsTable(e){const t=Array.from(new Set(e.clients.map(e=>null==e.vlan||""===e.vlan?null:String(e.vlan)).filter(Boolean))).sort((e,t)=>Number(e)-Number(t)),s=Array.from(new Set(e.clients.map(e=>e.ssid).filter(Boolean))).sort();let i=this._filter(e.clients,this._clientSearch);this._clientVlanFilter&&(i=i.filter(e=>String(e.vlan??"")===this._clientVlanFilter)),this._clientSsidFilter&&(i=i.filter(e=>e.ssid===this._clientSsidFilter)),i=Ze(i,this._clientSort,Bt.CLIENT_SORT);const r=this._paginate(i,this._clientPage,this._clientPageSize);return K`
      <div class="card" id="clients-card">
        <h3>Clients (${i.length})</h3>
        <div class="filters">
          <label
            >VLAN
            <select
              .value=${this._clientVlanFilter}
              @change=${e=>{this._clientVlanFilter=e.target.value,this._clientPage=0}}
            >
              <option value="">All</option>
              ${t.map(e=>K`<option value=${e} ?selected=${e===this._clientVlanFilter}>${e}</option>`)}
            </select>
          </label>
          <label
            >SSID
            <select
              .value=${this._clientSsidFilter}
              @change=${e=>{this._clientSsidFilter=e.target.value,this._clientPage=0}}
            >
              <option value="">All</option>
              ${s.map(e=>K`<option value=${e} ?selected=${e===this._clientSsidFilter}>${e}</option>`)}
            </select>
          </label>
          ${this._clientVlanFilter?K`<span class="active-filter" @click=${()=>this._clientVlanFilter=""}
                >VLAN ${this._clientVlanFilter} ✕</span
              >`:j}
          ${this._clientSsidFilter?K`<span class="active-filter" @click=${()=>this._clientSsidFilter=""}
                >SSID ${this._clientSsidFilter} ✕</span
              >`:j}
        </div>
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search client, IP, MAC, SSID, integration…"
            .value=${this._clientSearch}
            @input=${e=>{this._clientSearch=e.target.value,this._clientPage=0}}
          />
        </div>
        ${0===i.length?K`<div class="empty">No clients match.</div>`:K`
              <div class="table-wrap">
                <table>
                  <thead>
                    ${this._colHeaders()}
                  </thead>
                  <tbody>
                    ${r.map(e=>this._renderRow(e))}
                  </tbody>
                </table>
              </div>
              ${this._renderPager(i.length,this._clientPage,this._clientPageSize,e=>this._clientPage=e,e=>{this._clientPageSize=e,this._clientPage=0})}
            `}
        <div class="note">
          Columns shown as “—” aren't reported by this controller's API for that row.
          VLAN, IPv6, SSID, bandwidth, and last-seen availability depend on the UniFi
          firmware/API version.
        </div>
      </div>
    `}_renderDevicesTable(e){const t=Ze(this._filter(e.devices,this._deviceSearch),this._deviceSort,Bt.DEVICE_SORT),s=this._paginate(t,this._devicePage,this._devicePageSize),i=this._deviceSort,r=e=>{this._deviceSort=e,this._devicePage=0};return K`
      <div class="card">
        <h3>Network Devices (${t.length})</h3>
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search device, IP, MAC, integration…"
            .value=${this._deviceSearch}
            @input=${e=>{this._deviceSearch=e.target.value,this._devicePage=0}}
          />
        </div>
        ${0===t.length?K`<div class="empty">No network devices match.</div>`:K`
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      ${Qe("Device","name",i,r)}
                      ${Qe("IPv4","ipv4",i,r)}
                      ${Qe("MAC","mac",i,r)}
                      ${Qe("VLAN","vlan",i,r,{numeric:!0})}
                      ${Qe("Model","model",i,r)}
                      ${Qe("Firmware","firmware",i,r)}
                      ${Qe("Bandwidth","bandwidth",i,r)}
                      ${Qe("Last Seen","last_seen",i,r)}
                      ${Qe("Integration","integration",i,r)}
                    </tr>
                  </thead>
                  <tbody>
                    ${s.map(e=>this._renderDeviceRow(e))}
                  </tbody>
                </table>
              </div>
              ${this._renderPager(t.length,this._devicePage,this._devicePageSize,e=>this._devicePage=e,e=>{this._devicePageSize=e,this._devicePage=0})}
            `}
      </div>
    `}_renderFirmware(e){return null==e?K`<span class="muted">—</span>`:e?K`<span style="color:var(--status-warning);font-weight:600;">Update available</span>`:K`<span class="muted">Up to date</span>`}_renderDeviceRow(e){return K`
      <tr>
        <td>
          <div style="font-weight:600;">${e.name}</div>
          ${e.state?K`<div class="muted" style="font-size:11px;">${e.state.toLowerCase()}</div>`:j}
        </td>
        <td class="mono">${e.ipv4??"—"}</td>
        <td class="mono">${e.mac??"—"}</td>
        <td class="num">${this._fmtVlan(e.vlan)}</td>
        <td>${e.model??"—"}</td>
        <td>${this._renderFirmware(e.firmware_updatable)}</td>
        <td>${this._fmtBandwidth(e.bandwidth)}</td>
        <td>${this._fmtLastSeen(e.last_seen)}</td>
        <td>${this._renderMatch(e)}</td>
      </tr>
    `}_renderPager(e,t,s,i,r){const n="all"===s?1:Math.max(1,Math.ceil(e/s));return K`
      <div class="footer">
        <button class="ha-btn" ?disabled=${t<=0} @click=${()=>i(t-1)}>Prev</button>
        <span>Page ${t+1} of ${n}</span>
        <button class="ha-btn" ?disabled=${t>=n-1} @click=${()=>i(t+1)}>
          Next
        </button>
        <select
          @change=${e=>{const t=e.target.value;r("all"===t?"all":Number(t))}}
        >
          ${Ot.map(e=>K`<option value=${String(e)} ?selected=${e===s}>${"all"===e?"All":`${e} / page`}</option>`)}
        </select>
      </div>
    `}_renderProtectCard(e){const t=e.protect;return t.configured?t.reachable?K`
      <div class="card">
        <h3>
          UniFi Protect
          <span class="muted" style="font-weight:400;font-size:12px;">
            —
            <span class="dot ${t.cameras_online===t.camera_count?"good":"bad"}"></span>
            ${t.cameras_online} / ${t.camera_count} cameras online
          </span>
        </h3>
        ${this._renderProtectDevices(t.cameras)}
      </div>
      ${this._renderProtectEvents(t)}
    `:K`
        <div class="card">
          <h3>UniFi Protect</h3>
          <div class="muted" style="font-size:13px;">
            Configured but not reachable${t.error?K` — ${t.error}`:""}.
          </div>
        </div>
      `:j}_renderProtectDevices(e){if(!e.length)return K`<div class="empty">No Protect devices reported.</div>`;const t=this._protectSort,s=e=>this._protectSort=e,i=Ze(e.slice(),t,{name:e=>e.name,ip:e=>e.ip,mac:e=>e.mac,recording:e=>e.is_recording,last_ring:e=>e.last_ring,channels:e=>e.channel_count});return K`
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${Qe("Name","name",t,s)}
              ${Qe("IP","ip",t,s)}
              ${Qe("MAC","mac",t,s)}
              ${Qe("Recording","recording",t,s)}
              ${Qe("Last Ring","last_ring",t,s)}
              ${Qe("Channels","channels",t,s)}
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${i.map(e=>{const t=zt(e.link);return K`
                <tr>
                  <td>
                    <div style="font-weight:600;">
                      ${t?K`<a class="thumb-link" href=${t} target="_blank" rel="noopener"
                            >${e.name} ↗</a
                          >`:e.name}
                    </div>
                    ${e.state?K`<div class="muted" style="font-size:11px;">${e.state.toLowerCase()}</div>`:j}
                  </td>
                  <td class="mono">${e.ip??"—"}</td>
                  <td class="mono">${e.mac??"—"}</td>
                  <td>
                    ${null==e.is_recording?K`<span class="muted">—</span>`:e.is_recording?K`<span class="dot bad"></span>Recording`:K`<span class="muted">Off</span>`}
                  </td>
                  <td>${this._fmtLastSeen(e.last_ring)}</td>
                  <td title=${e.channels.join(", ")}>
                    ${e.channel_count?`${e.channel_count}${e.channels.length?` (${e.channels.join(", ")})`:""}`:"—"}
                  </td>
                  <td>
                    ${t?K`<a class="thumb-link" href=${t} target="_blank" rel="noopener">Open ↗</a>`:j}
                  </td>
                </tr>
              `})}
          </tbody>
        </table>
      </div>
      <div class="note">
        Device names link to that camera on the Protect console
        (<code>https://&lt;host&gt;/protect/dashboard/devices/&lt;id&gt;</code>).
      </div>
    `}_fmtDuration(e){if(null==e)return"—";if(e<60)return`${e}s`;const t=Math.floor(e/60);if(t<60)return`${t}m ${e%60}s`;return`${Math.floor(t/60)}h ${t%60}m`}_renderProtectEvents(e){return K`
      <div class="card">
        <h3>Events &amp; AI Smart Detections <span class="muted" style="font-weight:400;font-size:12px;">— last 24h</span></h3>
        ${e.events_error?K`<div class="note" style="font-size:13px;">${e.events_error}</div>`:e.events.length?K`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${Qe("Type","type",this._eventSort,e=>this._eventSort=e)}
                        ${Qe("Smart Detections","detections",this._eventSort,e=>this._eventSort=e)}
                        ${Qe("Score","score",this._eventSort,e=>this._eventSort=e,{numeric:!0})}
                        ${Qe("Start","start",this._eventSort,e=>this._eventSort=e)}
                        ${Qe("Duration","duration",this._eventSort,e=>this._eventSort=e,{numeric:!0})}
                        <th>Thumbnail</th>
                        ${Qe("License Plate","plate",this._eventSort,e=>this._eventSort=e)}
                      </tr>
                    </thead>
                    <tbody>
                      ${Ze(e.events.slice(),this._eventSort,{type:e=>e.type,detections:e=>e.smart_detect_types.join(", ")||null,score:e=>e.score,start:e=>e.start,duration:e=>e.duration,plate:e=>e.license_plate}).map(e=>K`
                          <tr>
                            <td>${e.type??"—"}</td>
                            <td>
                              ${e.smart_detect_types.length?K`<span class="chips"
                                    >${e.smart_detect_types.map(e=>K`<span class="chip">${e}</span>`)}</span
                                  >`:K`<span class="muted">—</span>`}
                            </td>
                            <td class="num">${null==e.score?"—":e.score}</td>
                            <td>${this._fmtLastSeen(e.start)}</td>
                            <td class="num">${this._fmtDuration(e.duration)}</td>
                            <td>
                              ${zt(e.thumbnail_link)?K`<a
                                    class="thumb-link"
                                    href=${zt(e.thumbnail_link)}
                                    target="_blank"
                                    rel="noopener"
                                    >view ↗</a
                                  >`:e.thumbnail?K`<span class="muted" title="Thumbnail exists but needs an authenticated fetch">available</span>`:K`<span class="muted">—</span>`}
                            </td>
                            <td>${e.license_plate?K`<span class="plate">${e.license_plate}</span>`:K`<span class="muted">—</span>`}</td>
                          </tr>
                        `)}
                    </tbody>
                  </table>
                </div>
              `:K`<div class="empty">No events in the last 24 hours.</div>`}
      </div>
    `}};It.styles=[qe,a`
      .wifi-ssid {
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 10px;
      }
      .wifi-head {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 6px;
      }
      .wifi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 4px 16px;
        font-size: 13px;
      }
      .wifi-grid .muted {
        display: block;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .wifi-filter {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
      }
      ul.findings {
        margin: 8px 0 0;
        padding: 0;
        list-style: none;
      }
      .finding {
        display: flex;
        gap: 8px;
        align-items: baseline;
        font-size: 13px;
        padding: 3px 0;
      }
      .finding .sev {
        flex: 0 0 auto;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-radius: 4px;
        padding: 1px 6px;
        background: var(--secondary-background-color, #f0f0f0);
      }
      .finding.blocking .sev {
        background: var(--error-color, #db4437);
        color: #fff;
      }
      .finding.possible .sev {
        background: var(--warning-color, #ffa600);
        color: #000;
      }
      .stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .stat-tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .stat-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--secondary-text-color);
      }
      .stat-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.1;
      }
      .stat-tile .sub {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
      }
      .dot.good {
        background: var(--status-good);
      }
      .dot.bad {
        background: var(--status-critical);
      }
      .dot.unknown {
        background: var(--cat-other);
      }
      .ssid-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .ssid-row {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
      }
      .ssid-row .name {
        min-width: 140px;
        font-weight: 600;
      }
      .ssid-row .bar {
        flex: 1;
        height: 8px;
        border-radius: 4px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        overflow: hidden;
      }
      .ssid-row .bar > span {
        display: block;
        height: 100%;
        background: var(--primary-color);
      }
      .ssid-row .count {
        min-width: 32px;
        text-align: right;
        font-variant-numeric: tabular-nums;
        font-weight: 700;
      }
      .ssid-row.clickable {
        cursor: pointer;
        border-radius: 6px;
        padding: 4px 6px;
        margin: -4px -6px;
      }
      .ssid-row.clickable:hover {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
      }
      .ssid-row.active {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.12);
      }
      .ssid-row.active .name {
        color: var(--primary-color);
      }
      .filters {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }
      .filters label {
        font-size: 12px;
        color: var(--secondary-text-color);
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .active-filter {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        background: var(--primary-color);
        color: #fff;
        padding: 4px 10px;
        border-radius: 100px;
        cursor: pointer;
      }
      .thumb-link {
        color: var(--primary-color);
        cursor: pointer;
        text-decoration: none;
      }
      .plate {
        font-family: var(--ha-font-family-code, monospace);
        font-weight: 700;
        letter-spacing: 0.06em;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        padding: 2px 6px;
        border-radius: 4px;
      }
      .table-wrap {
        overflow-x: auto;
      }
      .toolbar input {
        flex: 1;
        min-width: 180px;
      }
      td.num,
      th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
      }
      .mono {
        font-family: var(--ha-font-family-code, monospace);
        font-size: 12px;
      }
      .match {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 100px;
        cursor: pointer;
      }
      .match.failing {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      .match.healthy {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      .match.other {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        color: var(--secondary-text-color);
      }
      .alert {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.1);
        border: 1px solid var(--error-color, #db4437);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-size: 13.5px;
        color: var(--primary-text-color);
        line-height: 1.5;
      }
      .footer {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        color: var(--secondary-text-color);
      }
      .footer select {
        margin-left: auto;
      }
      .note {
        font-size: 11.5px;
        color: var(--secondary-text-color);
        margin-top: 8px;
        line-height: 1.5;
      }
    `],It.CLIENT_SORT={name:e=>e.name,ipv4:e=>e.ipv4,ipv6:e=>e.ipv6,mac:e=>e.mac,vlan:e=>null==e.vlan||""===e.vlan?null:Number(e.vlan),ssid:e=>e.ssid??(e.wired?"wired":null),uptime:e=>e.uptime,bandwidth:e=>e.bandwidth?.total_bytes??null,last_seen:e=>e.last_seen,integration:e=>e.integration_match?.domain??null},It.DEVICE_SORT={name:e=>e.name,ipv4:e=>e.ipv4,mac:e=>e.mac,vlan:e=>null==e.vlan||""===e.vlan?null:Number(e.vlan),model:e=>e.model,firmware:e=>e.firmware_updatable,bandwidth:e=>e.bandwidth?.total_bytes??null,last_seen:e=>e.last_seen,integration:e=>e.integration_match?.domain??null},e([ue({attribute:!1})],It.prototype,"initialClientFilter",void 0),e([pe()],It.prototype,"_overview",void 0),e([pe()],It.prototype,"_loading",void 0),e([pe()],It.prototype,"_error",void 0),e([pe()],It.prototype,"_clientSearch",void 0),e([pe()],It.prototype,"_clientPage",void 0),e([pe()],It.prototype,"_clientPageSize",void 0),e([pe()],It.prototype,"_clientVlanFilter",void 0),e([pe()],It.prototype,"_clientSsidFilter",void 0),e([pe()],It.prototype,"_clientSort",void 0),e([pe()],It.prototype,"_wifiSsidFilter",void 0),e([pe()],It.prototype,"_deviceSearch",void 0),e([pe()],It.prototype,"_devicePage",void 0),e([pe()],It.prototype,"_devicePageSize",void 0),e([pe()],It.prototype,"_deviceSort",void 0),e([pe()],It.prototype,"_protectSort",void 0),e([pe()],It.prototype,"_eventSort",void 0),It=Bt=e([he("ha-soc-network-view")],It);const Nt=/^([0-9a-f]{1,2}:){5}[0-9a-f]{1,2}$/i;function Ft(e){const t=e.split(".");if(4!==t.length)return null;let s=0;for(const e of t){if(!/^\d{1,3}$/.test(e))return null;const t=Number(e);if(t>255)return null;s=s<<8|t}return s>>>0}function Ht(e,t){const s=t.indexOf("/");if(s<0)return!1;const i=t.slice(0,s),r=Number(t.slice(s+1));if(!Number.isInteger(r)||r<0||r>32)return!1;const n=Ft(e),o=Ft(i);if(null===n||null===o)return!1;const a=0===r?0:4294967295<<32-r>>>0;return(n&a)===(o&a)}function Wt(e,t){const s=[];if(Nt.test(e)){const i=e.toLowerCase();for(const r of t)r.mac&&r.mac.toLowerCase()===i&&s.push({name:r.name||r.mac,matchedOn:e});return s}if(e.includes("/")){for(const i of t)i.ipv4&&Ht(i.ipv4,e)&&s.push({name:i.name||i.ipv4,matchedOn:i.ipv4});return s}for(const i of t)i.ipv4!==e&&i.ipv6!==e||s.push({name:i.name||e,matchedOn:e});return s}const Ut={networks:"Networks",zones:"Firewall zones",firewall_policies:"Firewall policies",acl_rules:"ACL rules",devices:"Devices"};let Kt=class extends Je{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._error=null,this._aclSort=null,this._firewallPolicySort=null,this._portSort=null,this._fwViewMode="table",this._fwZonePairFilter=null,this._suggestionBusy=null,this._suggestionError=null,this._ledger=null,this._ledgerBusy=!1,this._ledgerError=null,this._isOwner=!1,this._ssh=null,this._sshHost="",this._sshSelected=["whoami"],this._sshRun=null,this._sshBusy=!1,this._sshError=null}get viewId(){return"network_security"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{this._overview=await(e=this.hass,we(e,{type:"ha_soc/network_security/overview"}))}catch(e){this._error=e instanceof Error?e.message:String(e),this._overview=null}finally{this._loading=!1}var e;try{this._isOwner=!!(await Me(this.hass)).is_owner}catch{this._isOwner=!1}if(this._isOwner)try{this._ssh=await Ke(this.hass)}catch{this._ssh=null}try{this._ledger=await Ue(this.hass)}catch(e){this._ledger={available:!1,error:e instanceof Error?e.message:String(e),application_version:null,baseline:null,current:null,drift:null,history:[]}}}render(){if(this._loading)return K`<div class="card">Loading…</div>`;if(this._error)return K`<div class="card"><div class="alert">${this._error}</div></div>`;const e=this._overview;if(!e)return K`<div class="card">No data.</div>`;const t=[{id:"findings",title:"Suggestions",render:()=>this._renderFindings(e.findings)},{id:"firewall_policies",title:"Firewall Policies",render:()=>this._renderFirewallPolicies(e.firewall_policies,e.findings,e.write_enabled)},{id:"zone_matrix",title:"Zone Matrix",render:()=>this._renderZoneMatrixCard(e.firewall_policies)},{id:"acl",title:"ACL Rules",render:()=>this._renderAcl(e.acl)},{id:"config_ledger",title:"Configuration Baseline",render:()=>this._renderConfigLedger()},{id:"device_ssh",title:"Device SSH",render:()=>this._renderDeviceSsh()},{id:"server_ports",title:"Home Assistant Server Ports",render:()=>this._renderServerPorts(e.server_ports)},{id:"pihole",title:"Pi-hole DNS",render:()=>this._renderPihole(e.pihole)},{id:"technitium",title:"Technitium DNS",render:()=>this._renderTechnitium(e.technitium)}];return K`
      <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;align-items:center;">
        <button class="ha-btn" @click=${()=>this._load()}>Refresh</button>
        <span class="muted" style="font-size:12px;">
          ${e.write_enabled?"Advisory, except Apply on the Suggested changes tab, which disables the named rule or policy on the controller through the write-scoped key.":"Advisory only — nothing on this tab changes UniFi or Pi-hole configuration."}
        </span>
      </div>
      ${this._renderSections(t)}
    `}_renderDeviceSsh(){const e=this._ssh;return this._isOwner?e?K`
      <div class="card">
        <h3>Device SSH</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Read-only. Commands come from a fixed allowlist in the integration, so there is no
          way to send an arbitrary string to a device. Output is shown here and nowhere else:
          it is not stored, and the audit record keeps the outcomes, not the text. The one
          exception is the parsed Threat Management posture from ips_config, which is kept
          so the Suggestions above can use it between runs.
        </p>
        ${this._renderStoredIpsPosture()}

        ${e.enabled?j:K`<p class="muted">
              Collection is off. Turn it on under Settings, Device SSH Collection.
            </p>`}

        <h4 style="margin:14px 0 6px;font-size:13px;">Key</h4>
        ${e.has_keypair?K`
              <p class="muted" style="font-size:12px;">
                Paste this into the controller under Device Authentication, SSH Keys, then wait
                for the devices to re-provision. The private half stays in the secret store.
              </p>
              <pre class="ssh-key">${e.public_key}</pre>
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <button class="ha-btn" ?disabled=${this._sshBusy} @click=${()=>this._sshKey("generate")}>
                  Replace keypair
                </button>
                <button class="ha-btn" ?disabled=${this._sshBusy} @click=${()=>this._sshKey("clear")}>
                  Delete keypair
                </button>
              </div>
              <p class="muted" style="font-size:11.5px;">
                Replacing or deleting locks HA SOC out of every device until the controller
                pushes the new key.
              </p>
            `:K`
              <p class="muted" style="font-size:12px;">No keypair yet.</p>
              <button class="ha-btn" ?disabled=${this._sshBusy} @click=${()=>this._sshKey("generate")}>
                Generate keypair
              </button>
            `}

        <h4 style="margin:16px 0 6px;font-size:13px;">Run</h4>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;">
          <input
            type="text"
            placeholder="Device address"
            .value=${this._sshHost}
            @input=${e=>this._sshHost=e.target.value}
            style="padding:6px 8px;min-width:180px;"
          />
          <button
            class="ha-btn"
            ?disabled=${!e.enabled||!e.has_keypair||!this._sshHost.trim()||!this._sshSelected.length||this._sshBusy}
            @click=${()=>this._runSsh()}
          >
            ${this._sshBusy?"Running…":"Run selected"}
          </button>
          ${this._sshError?K`<span class="alert" style="font-size:12px;">${this._sshError}</span>`:j}
        </div>

        <div style="display:grid;gap:4px;margin-bottom:10px;">
          ${e.commands.map(e=>K`
              <label style="display:flex;gap:8px;align-items:flex-start;font-size:12.5px;">
                <input
                  type="checkbox"
                  .checked=${this._sshSelected.includes(e.id)}
                  @change=${t=>this._toggleSshCommand(e.id,t.target.checked)}
                />
                <span>
                  <code>${e.argv}</code>
                  ${e.verified?j:K`<span class="pill" style="margin-left:6px;">unverified</span>`}
                  <span class="muted" style="display:block;font-size:11.5px;">${e.description}</span>
                </span>
              </label>
            `)}
        </div>

        ${this._sshRun?this._renderSshRun(this._sshRun):j}
        ${Object.keys(e.host_keys).length?K`
              <h4 style="margin:16px 0 6px;font-size:13px;">Pinned host keys</h4>
              <table class="tbl">
                <thead><tr><th>Device</th><th>Fingerprint</th><th>Pinned</th><th></th></tr></thead>
                <tbody>
                  ${Object.entries(e.host_keys).map(([e,t])=>K`
                      <tr>
                        <td>${e}</td>
                        <td style="font-family:monospace;font-size:11.5px;">${t.fingerprint}</td>
                        <td>${new Date(t.pinned_at).toLocaleString()}</td>
                        <td>
                          <button class="ha-btn" @click=${()=>this._forgetHostKey(e)}>Forget</button>
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j}
      </div>
    `:K`<div class="card"><h3>Device SSH</h3><p class="muted">Loading…</p></div>`:K`
        <div class="card">
          <h3>Device SSH</h3>
          <p class="muted">Owner only. Every ha_soc/ssh command is refused for other accounts.</p>
        </div>
      `}_renderApLogAnalysis(e){return e.wireless_activity?e.clients.length?K`
      <table style="margin:6px 0;">
        <thead>
          <tr>
            <th>Client</th>
            <th>SSID VAP</th>
            <th>Attempts</th>
            <th>Stopped at</th>
            <th>Signal</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          ${e.clients.map(e=>K`
              <tr>
                <td class="mono">${e.mac}</td>
                <td>${e.vap??"—"}</td>
                <td>
                  ${e.attempts}
                  ${e.failures?K`<span class="muted">(${e.failures} failed)</span>`:j}
                </td>
                <td>
                  ${e.failures&&!e.ever_succeeded?K`<span class="pill pill-fail">${e.last_stage}</span>`:K`<span class="muted">${e.last_outcome}</span>`}
                </td>
                <td>
                  ${null!==e.worst_rssi?`${e.worst_rssi} dBm`:"—"}
                </td>
                <td>${e.last_reason??e.last_reason_code??"—"}</td>
              </tr>
            `)}
        </tbody>
      </table>
    `:K`<p class="muted" style="margin:6px 0;font-size:12px;">
        Wireless activity present, but no station-tracker records in this excerpt.
      </p>`:K`
        <div class="alert" style="margin:6px 0;">
          This log contains no wireless events, so it says nothing about who tried to join.
          ${e.controller_unreachable?K`It is also full of failed controller informs
                (${e.inform_failures} in this excerpt), which is what an access point that
                cannot reach the controller produces.`:j}
        </div>
      `}_renderStoredIpsPosture(){const e=this._overview?.ips_posture;return e?K`<p class="muted" style="font-size:12px;">
      Threat Management posture last read from <span class="mono">${e.host}</span> at
      <span class="mono">${e.collected_at.replace("T"," ").slice(0,19)}</span>:
      ${e.posture.mode}${e.posture.exempt_networks.length?`, ${e.posture.exempt_networks.length} network(s) never alerted on`:""}. Run ips_config again after changing the gateway.
    </p>`:K`<p class="muted" style="font-size:12px;">
        Threat Management has not been read yet. Run ips_config against the gateway to add
        the IDS coverage checks to Suggestions.
      </p>`}_renderAnalysis(e){return"ips_config"===e.kind?this._renderIpsPosture(e):"ips_block_log"===e.kind?this._renderIpsBlockLog(e):this._renderApLogAnalysis(e)}_renderIpsPosture(e){const t=Object.entries(e.parsed).filter(([,e])=>!e).map(([e])=>e),s="prevent"===e.mode?"good":"detect"===e.mode?"medium":"off"===e.mode?"high":"info",i=e=>null===e?"unknown":e?"yes":"no";return K`
      ${t.length?K`<div class="alert" style="margin:6px 0;">
            ${t.length} of 6 files did not come back (${t.join(", ")}). The lists
            below that depend on them are unknown, not empty.
          </div>`:j}
      <table style="margin:6px 0;">
        <tbody>
          <tr>
            <th>Mode</th>
            <td>
              <span class="pill ${s}"><span class="dot"></span>${e.mode}</span>
              ${"prevent"===e.mode?K`<span class="muted"> ${e.drop_categories.length} categories block${null!==e.block_time_seconds?`, ${e.block_time_seconds} s per block`:""}</span>`:"detect"===e.mode?K`<span class="muted"> ${e.alert_categories.length} categories alert, none block</span>`:j}
            </td>
          </tr>
          <tr>
            <th>Threat logging</th>
            <td>${i(e.logging_threat_event)}</td>
          </tr>
          <tr>
            <th>SSL inspection</th>
            <td>${i(e.ssl_inspection)}${null!==e.suricata_version?K`<span class="muted"> · Suricata ${e.suricata_version}</span>`:j}</td>
          </tr>
          <tr>
            <th>Never alerted on</th>
            <td>
              ${e.parsed.reputation||e.parsed.threshold?e.exempt_networks.length||e.suppressed_networks.length?K`<span class="mono">${[...new Set([...e.exempt_networks,...e.suppressed_networks])].join(", ")}</span>
                      <span class="muted"> (allowlisted in both directions for every signature)</span>`:"none":"unknown"}
            </td>
          </tr>
          <tr>
            <th>HOME_NET</th>
            <td>${e.parsed.homenet?K`<span class="mono">${e.home_networks.join(", ")}</span>`:"unknown"}</td>
          </tr>
          <tr>
            <th>Inspected interfaces</th>
            <td>${e.parsed.interfaces?K`<span class="mono">${e.interfaces.map(e=>e.interface).join(", ")}</span>`:"unknown"}</td>
          </tr>
        </tbody>
      </table>
    `}_renderIpsBlockLog(e){if(!e.rows.length)return K`<p class="muted" style="margin:6px 0;font-size:12px;">
        No threat or firewall-policy blocks in the controller's alert collection${e.unparsed?` (${e.unparsed} line(s) could not be read)`:""}.
      </p>`;const t=e=>e.name?K`${e.name}<span class="muted"> ${e.address??e.mac??""}</span>`:K`<span class="mono">${e.address??e.mac??"—"}</span>`;return K`
      <p class="muted" style="margin:6px 0;font-size:12px;">
        Last 24 h: ${e.threat_blocks_24h} threat block(s), ${e.firewall_blocks_24h} policy block(s),
        ${e.sources_24h.length} distinct source(s). Showing the newest ${e.rows.length}.
        ${e.unparsed?`${e.unparsed} line(s) could not be read.`:""}
      </p>
      <div class="table-wrap">
        <table style="margin:6px 0;">
          <thead>
            <tr>
              <th>When</th>
              <th>What</th>
              <th>Severity</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Policy</th>
            </tr>
          </thead>
          <tbody>
            ${e.rows.map(e=>K`
                <tr>
                  <td class="mono">${e.time?e.time.replace("T"," ").slice(0,19):"—"}</td>
                  <td>${"threat"===e.kind?"Threat":"firewall"===e.kind?"Policy":e.key}</td>
                  <td>${e.severity?K`<span class="pill ${"VERY_HIGH"===e.severity||"HIGH"===e.severity?"high":"medium"}"><span class="dot"></span>${e.severity.toLowerCase().replace("_"," ")}</span>`:"—"}</td>
                  <td>${t(e.source)}</td>
                  <td>${t(e.destination)}</td>
                  <td>${e.policy??"—"}</td>
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `}_renderSshRun(e){return K`
      <p class="muted" style="font-size:12px;">
        ${e.host} as ${e.username} &middot; host key ${e.host_key_fingerprint}
        ${e.host_key_pinned_now?" (pinned on this connection)":""}
      </p>
      ${e.results.map(e=>K`
          <div style="margin-bottom:10px;">
            <div style="display:flex;gap:8px;align-items:center;">
              <span class="pill pill-${e.state}">${e.state}</span>
              <code>${e.argv}</code>
              ${null!==e.exit_status?K`<span class="muted" style="font-size:11.5px;">exit ${e.exit_status}</span>`:j}
            </div>
            ${e.analysis?this._renderAnalysis(e.analysis):j}
            ${e.stdout?K`<pre class="ssh-out">${e.stdout}</pre>`:j}
            ${e.stderr?K`<pre class="ssh-out ssh-err">${e.stderr}</pre>`:j}
          </div>
        `)}
    `}_toggleSshCommand(e,t){this._sshSelected=t?[...this._sshSelected,e]:this._sshSelected.filter(t=>t!==e)}async _sshKey(e){this._sshBusy=!0,this._sshError=null;try{"generate"===e?await(t=this.hass,we(t,{type:"ha_soc/ssh/generate_key"})):await(e=>we(e,{type:"ha_soc/ssh/clear_key"}))(this.hass),this._ssh=await Ke(this.hass)}catch(e){this._sshError=e.message||String(e)}finally{this._sshBusy=!1}var t}async _forgetHostKey(e){try{await((e,t)=>we(e,{type:"ha_soc/ssh/forget_host_key",host:t}))(this.hass,e),this._ssh=await Ke(this.hass)}catch(e){this._sshError=e.message||String(e)}}async _runSsh(){this._sshBusy=!0,this._sshError=null,this._sshRun=null;try{this._sshRun=await(e=this.hass,t=this._sshHost.trim(),s=this._sshSelected,we(e,{type:"ha_soc/ssh/run",host:t,command_ids:s})),this._ssh=await Ke(this.hass)}catch(e){const t=e;this._sshError=t.message||String(e)}finally{this._sshBusy=!1}var e,t,s}_renderConfigLedger(){const e=this._ledger;if(!e)return K`<div class="card"><h3>Configuration Baseline</h3><p class="muted">Loading…</p></div>`;if(!e.available)return K`
        <div class="card">
          <h3>Configuration Baseline</h3>
          <p class="muted">
            ${e.error||"The controller configuration could not be read completely, so no comparison is made."}
            A partial read is not compared: rules that failed to load would look deleted.
          </p>
        </div>
      `;const t=e.drift,s=t&&t.total>0;return K`
      <div class="card">
        <h3>
          Configuration Baseline
          ${e.application_version?K`<span class="muted" style="font-weight:400;font-size:12px;">
                &nbsp;UniFi Network ${e.application_version}</span>`:j}
        </h3>

        ${e.baseline?K`
              <p class="muted">
                Baseline accepted ${new Date(e.baseline.accepted_at).toLocaleString()}.
                ${s?K`<strong>${t.total}</strong> change${1===t.total?"":"s"} since.`:"The controller matches it."}
              </p>
            `:K`
              <p class="muted">
                No baseline accepted yet. Review the networks, zones, policies, and ACL rules
                below, then accept them; every later change is compared against that record.
              </p>
            `}

        ${s?this._renderDriftTable(t):j}

        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px;">
          <button
            class="ha-btn"
            ?disabled=${!this._isOwner||this._ledgerBusy||!e.current}
            @click=${()=>this._acceptBaseline()}
          >
            ${e.baseline?"Accept current as new baseline":"Accept current as baseline"}
          </button>
          ${this._isOwner?j:K`<span class="muted" style="font-size:12px;">Owner only.</span>`}
          ${this._ledgerError?K`<span class="alert" style="font-size:12px;">${this._ledgerError}</span>`:j}
        </div>

        ${e.history.length?K`
              <h4 style="margin:16px 0 6px;font-size:13px;">Recorded changes</h4>
              <table class="tbl">
                <thead>
                  <tr><th>Observed</th><th>Changes</th><th>Sections</th></tr>
                </thead>
                <tbody>
                  ${e.history.map(e=>K`
                      <tr>
                        <td>${new Date(e.at).toLocaleString()}</td>
                        <td>${e.total}</td>
                        <td class="muted">
                          ${Object.entries(e.sections).map(([e,t])=>`${Ut[e]||e} (${t})`).join(", ")}
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j}
      </div>
    `}_renderDriftTable(e){const t=Object.entries(e.sections).filter(([,e])=>e.count>0);return K`
      <table class="tbl">
        <thead>
          <tr><th>Section</th><th>Added</th><th>Removed</th><th>Changed</th><th>Order</th></tr>
        </thead>
        <tbody>
          ${t.map(([e,t])=>K`
              <tr>
                <td>${Ut[e]||e}</td>
                <td>${t.added.length||""}</td>
                <td>${t.removed.length||""}</td>
                <td>${t.changed.length||""}</td>
                <td>${t.ordering_changed?"changed":""}</td>
              </tr>
            `)}
        </tbody>
      </table>
      ${t.map(([e,t])=>t.changed.length?K`
              <div style="margin-top:10px;">
                <div class="muted" style="font-size:12px;font-weight:600;">
                  ${Ut[e]||e}
                </div>
                ${t.changed.map(e=>K`
                    <div style="font-size:12.5px;margin-top:4px;">
                      ${e.name||e.id}:
                      ${e.changes.map(e=>`${e.field} ${JSON.stringify(e.from)} → ${JSON.stringify(e.to)}`).join("; ")}
                    </div>
                  `)}
              </div>
            `:j)}
    `}async _acceptBaseline(){const e=this._ledger?.current;if(e){this._ledgerBusy=!0,this._ledgerError=null;try{await(t=this.hass,s=e.digest,we(t,{type:"ha_soc/unifi_ledger/accept",digest:s})),this._ledger=await Ue(this.hass)}catch(e){const t=e;this._ledgerError="stale_snapshot"===t.code?"The configuration changed while this page was open. Refresh, review the change, then accept.":t.message||String(e)}finally{this._ledgerBusy=!1}var t,s}}_renderFindings(e){const t=e.filter(e=>"ignored"!==e.decision?.status),s=e.length-t.length;return K`
      <div class="card">
        <h3>
          Suggestions
          ${s?K`<span class="muted" style="font-weight:400;font-size:12px;"
                >— ${s} ignored (see Suggested changes under Firewall Policies)</span
              >`:j}
        </h3>
        ${t.length?K`${t.map(e=>K`
                <div class="finding">
                  <div class="sev ${e.severity}" title=${e.severity}></div>
                  <div>
                    <div class="finding-title">
                      ${e.title}${this._renderDecisionBadge(e)}
                    </div>
                    <div class="finding-detail">${e.detail}</div>
                  </div>
                </div>
              `)}`:K`<div class="empty">Nothing stood out — no advisory findings right now.</div>`}
      </div>
    `}_renderDecisionBadge(e){const t=e.decision?.status;if(!t)return j;return K`<span class="badge-custom" style="margin-left:6px;">${"applied"===t?"applied":"planned"===t?"planned":"ignored"}</span>`}async _onSuggestionDecision(e,t){this._suggestionError=null,this._suggestionBusy=e.id;try{await((e,t,s)=>we(e,{type:"ha_soc/network_security/suggestion_set",finding_id:t,status:s}))(this.hass,e.id,t),await this._load()}catch(e){this._suggestionError=e instanceof Error?e.message:String(e)}finally{this._suggestionBusy=null}}async _onSuggestionApply(e){if(!e.remediation)return;if(window.confirm(`${e.remediation.label} on the UniFi controller now?\n\nThis is a real configuration change made with the write-scoped key. To undo: ${e.remediation.reversible}`)){this._suggestionError=null,this._suggestionBusy=e.id;try{await(t=this.hass,s=e.id,we(t,{type:"ha_soc/network_security/suggestion_apply",finding_id:s})),await this._load()}catch(e){this._suggestionError=e instanceof Error?e.message:String(e)}finally{this._suggestionBusy=null}var t,s}}_renderSuggestedChanges(e,t){return e.length?K`
      <p class="muted" style="font-size:12px;margin:0 0 8px;">
        Plan marks a change you intend to make by hand; Ignore hides it from the Suggestions card until
        you clear it. ${t?"Apply performs the named change on the controller with the write-scoped key and reads it back.":"Apply becomes available when suggestion write-back is enabled in Settings with a write-scoped key."}
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Suggestion</th>
              <th>Change</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${e.map(e=>{const s=e.decision?.status??null,i=this._suggestionBusy===e.id;return K`
                <tr>
                  <td><span class="match ${"high"===e.severity?"failing":"medium"===e.severity?"other":"healthy"}">${e.severity}</span></td>
                  <td style="font-weight:600;">
                    ${e.title}<span class="sub">${e.detail}</span>
                  </td>
                  <td>
                    ${e.remediation?K`${e.remediation.label}<span class="sub">Undo: ${e.remediation.reversible}</span>`:K`<span class="muted">manual — see the suggestion text</span>`}
                  </td>
                  <td>
                    ${s?K`${s}${e.decision?.at?K`<span class="sub">${new Date(e.decision.at).toLocaleString()}</span>`:j}`:K`<span class="muted">open</span>`}
                  </td>
                  <td style="white-space:nowrap;">
                    ${"applied"===s?j:K`
                          ${"planned"!==s?K`<button class="ha-btn" ?disabled=${i} @click=${()=>this._onSuggestionDecision(e,"planned")}>Plan</button>`:j}
                          ${"ignored"!==s?K`<button class="ha-btn" ?disabled=${i} @click=${()=>this._onSuggestionDecision(e,"ignored")}>Ignore</button>`:j}
                          ${s?K`<button class="ha-btn" ?disabled=${i} @click=${()=>this._onSuggestionDecision(e,null)}>Clear</button>`:j}
                          ${e.remediation&&t?K`<button class="ha-btn danger" ?disabled=${i} @click=${()=>this._onSuggestionApply(e)}>Apply</button>`:j}
                        `}
                  </td>
                </tr>
              `})}
          </tbody>
        </table>
      </div>
      ${this._suggestionError?K`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:8px;">${this._suggestionError}</p>`:j}
    `:K`<div class="empty">No suggested changes right now.</div>`}_renderCustomBadge(e){return e?K`<span class="badge-custom">custom</span>`:j}_customCountLabel(e){const t=e.filter(e=>null!=e.custom);if(!t.length)return"";const s=t.filter(e=>e.custom).length;return` · ${s} custom / ${e.length} total`}_renderDeviceChips(e){const t=function(e,t){if(!e.length||!t.length)return[];const s=new Set,i=[];for(const r of e)for(const e of Wt(r,t)){const t=`${e.name}\0${e.matchedOn}`;s.has(t)||(s.add(t),i.push(e))}return i}(e,this._overview?.clients??[]),s=t.slice(0,6);if(!s.length)return j;const i=t.length-s.length;return K`
      <span class="sub" style="display:block;margin-top:3px;">
        ${s.map(e=>K`
            <button
              class="device-chip"
              title="Jump to ${e.name} on the Network tab"
              @click=${()=>fe(this,"network",e.matchedOn)}
            >
              📟 ${e.name}
            </button>
          `)}${i>0?K`<span class="muted" style="font-size:10.5px;">+${i} more</span>`:j}
      </span>
    `}_policyActionClass(e){const t=(e??"").toLowerCase();return"allow"===t?"healthy":"block"===t||"reject"===t?"failing":"other"}_renderFirewallPolicies(e,t,s){const i=this._fwZonePairFilter?e.rules.filter(e=>e.source.zone===this._fwZonePairFilter.src&&e.destination.zone===this._fwZonePairFilter.dst):e.rules;return K`
      <div class="card">
        <h3>
          Firewall Policies — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— UniFi's default zone-based allow/deny view; order matters, evaluated top
            to bottom${this._customCountLabel(e.rules)}</span
          >
        </h3>
        <div class="view-toggle">
          <button
            class=${"table"===this._fwViewMode?"active":""}
            @click=${()=>this._fwViewMode="table"}
          >
            Table
          </button>
          <button
            class=${"suggestions"===this._fwViewMode?"active":""}
            @click=${()=>this._fwViewMode="suggestions"}
          >
            Suggested changes${t.length?` (${t.length})`:""}
          </button>
        </div>
        ${"suggestions"===this._fwViewMode?this._renderSuggestedChanges(t,s):e.available?e.rules.length?this._renderFirewallPolicyTable(i):K`<div class="empty">No Firewall Policies configured.</div>`:K`
                <div class="note" style="font-size:13px;">
                  Couldn't read Firewall Policies from this controller.${e.error?K` ${e.error}`:""}
                </div>
              `}
      </div>
    `}_renderZoneMatrixCard(e){return K`
      <div class="card">
        <h3>
          Zone Matrix
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— dominant policy per source and destination zone; click a cell to filter the policy table</span
          >
        </h3>
        ${e.available?e.zones.length?this._renderZoneMatrix(e):K`<div class="empty">No zones reported by this controller.</div>`:K`<div class="note" style="font-size:13px;">Couldn't read Firewall Policies from this controller.</div>`}
      </div>
    `}_renderFirewallPolicyTable(e){return K`
      ${this._fwZonePairFilter?K`
            <div class="zone-pair-filter">
              <span class="chip"
                >${this._fwZonePairFilter.src} → ${this._fwZonePairFilter.dst}</span
              >
              <button
                style="cursor:pointer;border:none;background:none;color:var(--primary-color);font-size:12px;"
                @click=${()=>this._fwZonePairFilter=null}
              >
                Clear filter
              </button>
            </div>
          `:j}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${Qe("#","order",this._firewallPolicySort,e=>this._firewallPolicySort=e,{numeric:!0})}
              ${Qe("Name","name",this._firewallPolicySort,e=>this._firewallPolicySort=e)}
              ${Qe("Action","action",this._firewallPolicySort,e=>this._firewallPolicySort=e)}
              ${Qe("Source zone","source_zone",this._firewallPolicySort,e=>this._firewallPolicySort=e)}
              ${Qe("Dest. zone","dest_zone",this._firewallPolicySort,e=>this._firewallPolicySort=e)}
              ${Qe("Protocol","protocol",this._firewallPolicySort,e=>this._firewallPolicySort=e)}
              ${Qe("Ports","ports",this._firewallPolicySort,e=>this._firewallPolicySort=e)}
              ${Qe("Enabled","enabled",this._firewallPolicySort,e=>this._firewallPolicySort=e)}
            </tr>
          </thead>
          <tbody>
            ${e.length?Ze(e.slice(),this._firewallPolicySort,{order:e=>e.order,name:e=>e.name,action:e=>e.action,source_zone:e=>e.source.zone,dest_zone:e=>e.destination.zone,protocol:e=>e.protocol,ports:e=>e.ports.length,enabled:e=>e.enabled}).map((e,t)=>this._renderFirewallPolicyRow(e,t)):K`<tr><td colspan="8"><div class="empty">No policies for this zone pair.</div></td></tr>`}
          </tbody>
        </table>
      </div>
      <div class="note">
        Every policy is scoped to a source/destination zone pair; the detail line under
        each name shows any additional network/IP/MAC/domain narrowing the controller
        reported, and a resolved device chip when it matches a known client.
      </div>
    `}_renderZoneMatrix(e){if(!e.zones.length)return K`<div class="empty">No firewall zones reported by this controller.</div>`;const t=function(e,t){const s=e.map(e=>e.name);return s.map(e=>s.map(s=>{const i=t.filter(t=>t.source.zone===e&&t.destination.zone===s),r=i.filter(e=>!1!==e.enabled),n=r.filter(e=>"ALLOW"===e.action).length,o=r.filter(e=>"BLOCK"===e.action||"REJECT"===e.action).length;let a="none";return n&&o?a="mixed":n?a="allow":o&&(a="block"),{srcZone:e,dstZone:s,policies:i,allowCount:n,blockCount:o,dominant:a}}))}(e.zones,e.rules),s=e.zones.map(e=>e.name);return K`
      <div class="matrix-wrap">
        <table class="zone-matrix">
          <thead>
            <tr>
              <th class="corner"></th>
              ${s.map(e=>K`<th>${e}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${t.map((e,t)=>K`
                <tr>
                  <th>${s[t]}</th>
                  ${e.map(e=>K`
                      <td
                        class="cell ${e.dominant}"
                        title="${e.policies.length} polic${1===e.policies.length?"y":"ies"}"
                        @click=${()=>this._selectZonePair(e.srcZone,e.dstZone)}
                      >
                        ${"none"===e.dominant?"—":"mixed"===e.dominant?"mixed":"allow"===e.dominant?"allow":"block"}${e.policies.length?K`<br /><span style="font-size:10px;">${e.policies.length}</span>`:j}
                      </td>
                    `)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
      <div class="note">
        Rows are the source zone, columns the destination zone. Click a cell to see its
        policies. "mixed" means both allow and block/reject policies exist for that pair
        — which one actually governs a given connection depends on evaluation order and
        UniFi's own implicit-deny fallback, neither of which this project models; open
        the filtered table to read the real order.
      </div>
    `}_selectZonePair(e,t){this._fwZonePairFilter={src:e,dst:t},this._fwViewMode="table"}_renderFirewallPolicyRow(e,t){const s=e=>{const t=[];return e.networks.length&&t.push(`networks: ${e.networks.join(", ")}`),e.ip_or_subnets.length&&t.push(`IP: ${e.ip_or_subnets.join(", ")}`),e.macs.length&&t.push(`MAC: ${e.macs.join(", ")}`),e.domains.length&&t.push(`domains: ${e.domains.join(", ")}`),e.applications.length&&t.push(`${e.applications.length} app(s)`),e.application_categories.length&&t.push(`${e.application_categories.length} app categor${1===e.application_categories.length?"y":"ies"}`),!t.length&&e.filter_type&&t.push(e.filter_type.toLowerCase().replace(/_/g," ")),t.join(" · ")},i=s(e.source),r=s(e.destination),n=[i&&`from ${i}`,r&&`to ${r}`].filter(Boolean).join(" · "),o=[...e.source.ip_or_subnets,...e.source.macs,...e.destination.ip_or_subnets,...e.destination.macs];return K`
      <tr>
        <td class="num">${e.order??t+1}</td>
        <td style="font-weight:600;">
          ${e.name??"—"}${this._renderCustomBadge(e.custom)}${n?K`<span class="sub">${n}</span>`:j}${this._renderDeviceChips(o)}
        </td>
        <td>
          ${e.action?K`<span class="match ${this._policyActionClass(e.action)}">${e.action}</span>`:K`<span class="muted">—</span>`}${e.allow_return_traffic?K`<span class="sub">+ mirrored return-traffic policy</span>`:j}
        </td>
        <td>${e.source.zone??K`<span class="muted">—</span>`}</td>
        <td>${e.destination.zone??K`<span class="muted">—</span>`}</td>
        <td>${e.protocol??K`<span class="muted">any</span>`}</td>
        <td>
          ${e.ports.length?K`<span class="mono">${e.ports.join(", ")}</span>`:e.source.ports_from_list||e.destination.ports_from_list?K`<span class="muted">traffic matching list</span>`:K`<span class="muted">any</span>`}
        </td>
        <td>
          ${null==e.enabled?K`<span class="muted">—</span>`:e.enabled?"yes":K`<span class="muted">disabled</span>`}
        </td>
      </tr>
    `}_aclActionClass(e){const t=(e??"").toLowerCase();return["allow","accept","permit"].some(e=>t.includes(e))?"healthy":["deny","drop","block","reject"].some(e=>t.includes(e))?"failing":"other"}_renderAcl(e){return K`
      <div class="card" id="acl-card">
        <h3>
          ACL Rules — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— order matters; rules are evaluated top to bottom${e.endpoint?` · source: ${e.endpoint}`:""}${this._customCountLabel(e.rules)}</span
          >
        </h3>
        ${e.available?e.rules.length?K`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${Qe("#","order",this._aclSort,e=>this._aclSort=e,{numeric:!0})}
                        ${Qe("Name","name",this._aclSort,e=>this._aclSort=e)}
                        ${Qe("Action","action",this._aclSort,e=>this._aclSort=e)}
                        ${Qe("Protocols","protocols",this._aclSort,e=>this._aclSort=e)}
                        ${Qe("Networks","networks",this._aclSort,e=>this._aclSort=e)}
                        ${Qe("Ports","ports",this._aclSort,e=>this._aclSort=e,{numeric:!0})}
                        ${Qe("Enabled","enabled",this._aclSort,e=>this._aclSort=e)}
                      </tr>
                    </thead>
                    <tbody>
                      ${Ze(e.rules.slice(),this._aclSort,{order:e=>e.order,name:e=>e.name,action:e=>e.action,protocols:e=>e.protocols.join(", ")||null,networks:e=>e.networks.join(", ")||null,ports:e=>e.ports.length,enabled:e=>e.enabled}).map((e,t)=>this._renderAclRow(e,t))}
                    </tbody>
                  </table>
                </div>
                <div class="note">
                  Order reflects evaluation precedence as returned by the controller. Source
                  and destination detail (IP/subnet, MAC, port scoping) is shown under each
                  rule's name when the controller reported it.
                </div>
              `:K`<div class="empty">No ACL rules configured (endpoint: ${e.endpoint}).</div>`:K`
              <div class="note" style="font-size:13px;">
                This controller's Integration API didn't return ACL rules. Endpoints tried:
                <code>${e.endpoints_tried.join(", ")||"—"}</code>.${e.error?K` Last response: ${e.error}.`:""}
              </div>
            `}
      </div>
    `}_renderAclRow(e,t){const s=[];e.source.ip_or_subnets.length&&s.push(`from ${e.source.ip_or_subnets.join(", ")}`),e.source.macs.length&&s.push(`MAC ${e.source.macs.join(", ")}`);const i=[];e.destination.ip_or_subnets.length&&i.push(`to ${e.destination.ip_or_subnets.join(", ")}`),e.destination.macs.length&&i.push(`MAC ${e.destination.macs.join(", ")}`);const r=[...s,...i].join(" · "),n=[...e.source.ip_or_subnets,...e.source.macs,...e.destination.ip_or_subnets,...e.destination.macs];return K`
      <tr>
        <td class="num">${e.order??t+1}</td>
        <td style="font-weight:600;">
          ${e.name??"—"}${this._renderCustomBadge(e.custom)}${r?K`<span class="sub">${r}</span>`:j}${this._renderDeviceChips(n)}
        </td>
        <td>
          ${e.action?K`<span class="match ${this._aclActionClass(e.action)}">${e.action}</span>`:K`<span class="muted">—</span>`}
        </td>
        <td>${e.protocols.length?e.protocols.join(", "):K`<span class="muted">any</span>`}</td>
        <td>
          ${e.networks.length?K`<span class="chips">${e.networks.map(e=>K`<span class="chip">${e}</span>`)}</span>`:K`<span class="muted">any / —</span>`}
        </td>
        <td>
          ${e.ports.length?K`<span class="mono">${e.ports.join(", ")}</span>`:K`<span class="muted">any</span>`}
        </td>
        <td>
          ${null==e.enabled?K`<span class="muted">—</span>`:e.enabled?"yes":K`<span class="muted">disabled</span>`}
        </td>
      </tr>
    `}_portStatusClass(e){return"covered"===e?"healthy":"uncovered"===e?"failing":"other"}_renderServerPorts(e){return K`
      <div class="card">
        <h3>
          Home Assistant Server Ports
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— cross-referenced against the ACL rules above</span
          >
        </h3>
        ${e.available?K`
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      ${Qe("Port","port",this._portSort,e=>this._portSort=e,{numeric:!0})}
                      ${Qe("Proto","proto",this._portSort,e=>this._portSort=e)}
                      ${Qe("Address","address",this._portSort,e=>this._portSort=e)}
                      ${Qe("Process","process",this._portSort,e=>this._portSort=e)}
                      ${Qe("Coverage","status",this._portSort,e=>this._portSort=e)}
                    </tr>
                  </thead>
                  <tbody>
                    ${Ze(e.ports.slice(),this._portSort,{port:e=>e.port,proto:e=>e.proto,address:e=>e.address,process:e=>e.process,status:e=>e.status}).map(e=>K`
                        <tr>
                          <td class="num">${e.port}</td>
                          <td>${e.proto??"—"}</td>
                          <td class="mono">${e.address??"—"}</td>
                          <td>${e.process??"—"}</td>
                          <td>
                            <span class="match ${this._portStatusClass(e.status)}">
                              ${"covered"===e.status?`covered by ${e.covered_by.join(", ")}`:"network_scoped"===e.status?`network-scoped: ${e.network_scoped_by.join(", ")}`:"uncovered"}
                            </span>
                          </td>
                        </tr>
                      `)}
                  </tbody>
                </table>
              </div>
              <div class="note">
                "Uncovered" means no enabled ACL rule names this server's IP/subnet as a
                destination for that port — it does not by itself mean the port is reachable
                from every network; UniFi's own default zone policy still applies.
                "Network-scoped" means a rule covers it by network/zone rather than by IP,
                which this project can't independently verify covers this server.
              </div>
            `:K`
              <div class="empty">
                No listening-port report from the HA SOC Probe add-on yet, or none of its
                reported bind addresses are real LAN addresses. Install/enable the Probe
                add-on to populate this.
              </div>
            `}
      </div>
    `}_renderPihole(e){return e.configured?e.reachable?K`
      <div class="card">
        <h3>Pi-hole DNS</h3>
        <div class="stat-row">
          <div class="stat-tile">
            <span class="label">Blocking</span>
            <span class="value">${e.blocking_enabled?"On":"Off"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Queries (24h window)</span>
            <span class="value">${e.summary?.total??"—"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Blocked</span>
            <span class="value"
              >${e.summary?.blocked??"—"}${null!=e.summary?.percent_blocked?` (${e.summary.percent_blocked.toFixed(1)}%)`:""}</span
            >
          </div>
          <div class="stat-tile">
            <span class="label">IoT subnet scoped</span>
            <span class="value">
              ${null==e.iot_cidr?K`<span class="muted" style="font-size:16px;">not set</span>`:e.iot_clients_scoped?"Yes":K`<span style="color:var(--status-warning, #fab219);">No</span>`}
            </span>
          </div>
        </div>
        ${e.top_blocked_domains.length||e.recent_blocked.length?K`
              <div class="stat-row" style="margin-top:12px;">
                ${e.top_blocked_domains.length?K`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Top blocked domains</span>
                        <div class="domain-list">
                          ${e.top_blocked_domains.map(e=>K`<div class="row"><span>${e.domain}</span><span>${e.count}</span></div>`)}
                        </div>
                      </div>
                    `:j}
                ${e.recent_blocked.length?K`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Recently blocked</span>
                        <div class="domain-list">
                          ${e.recent_blocked.map(e=>K`<div class="row"><span>${e}</span></div>`)}
                        </div>
                      </div>
                    `:j}
              </div>
            `:j}
      </div>
    `:K`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="alert">${e.error??"Pi-hole is not reachable."}</div>
        </div>
      `:K`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="empty">
            Not connected. Add a Pi-hole host and app password in Settings to see blocking
            status, IoT client group scoping, and recently blocked domains here.
          </div>
        </div>
      `}_renderTechnitium(e){if(!e.configured)return K`
        <div class="card">
          <h3>Technitium DNS</h3>
          <div class="empty">
            Not connected. Add a Technitium host and API token in Settings to see blocking
            status, DNS zones/records, and recently blocked domains here.
          </div>
        </div>
      `;if(!e.reachable)return K`
        <div class="card">
          <h3>Technitium DNS</h3>
          <div class="alert">${e.error??"Technitium is not reachable."}</div>
        </div>
      `;const t=Object.entries(e.records).flatMap(([e,t])=>t.map(t=>({zone:e,...t})));return K`
      <div class="card">
        <h3>Technitium DNS</h3>
        <div class="stat-row">
          <div class="stat-tile">
            <span class="label">Blocking</span>
            <span class="value">${e.blocking_enabled?"On":"Off"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Queries (last hour)</span>
            <span class="value">${e.summary?.total??"—"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Blocked</span>
            <span class="value"
              >${e.summary?.blocked??"—"}${null!=e.summary?.percent_blocked?` (${e.summary.percent_blocked.toFixed(1)}%)`:""}</span
            >
          </div>
          <div class="stat-tile">
            <span class="label">Zones</span>
            <span class="value">${e.zones.length}</span>
          </div>
        </div>
        ${t.length?K`
              <div class="stat-row" style="margin-top:12px;">
                <div class="stat-tile" style="grid-column: span 4;">
                  <span class="label">DNS records</span>
                  <div class="domain-list">
                    ${t.map(e=>K`<div class="row">
                          <span>${e.zone} / ${e.name} (${e.type})</span>
                          <span>${JSON.stringify(e.data)}</span>
                        </div>`)}
                  </div>
                </div>
              </div>
            `:j}
        ${e.top_blocked_domains.length||e.recent_blocked.length?K`
              <div class="stat-row" style="margin-top:12px;">
                ${e.top_blocked_domains.length?K`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Top blocked domains</span>
                        <div class="domain-list">
                          ${e.top_blocked_domains.map(e=>K`<div class="row"><span>${e.domain}</span><span>${e.count}</span></div>`)}
                        </div>
                      </div>
                    `:j}
                ${e.recent_blocked.length?K`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Recently blocked</span>
                        <div class="domain-list">
                          ${e.recent_blocked.map(e=>K`<div class="row"><span>${e}</span></div>`)}
                        </div>
                      </div>
                    `:j}
              </div>
            `:j}
      </div>
    `}};Kt.styles=[qe,a`
      .ssh-key,
      .ssh-out {
        background: rgba(127, 127, 127, 0.1);
        border: 1px solid var(--divider-color, #444);
        border-radius: 4px;
        padding: 8px;
        font-size: 11.5px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-all;
        overflow-x: auto;
        max-height: 320px;
      }
      .ssh-out.ssh-err {
        border-color: var(--error-color, #db4437);
      }
      .pill-pass {
        background: var(--success-color, #43a047);
        color: #fff;
      }
      .pill-fail {
        background: var(--error-color, #db4437);
        color: #fff;
      }
      .pill-unknown {
        background: var(--warning-color, #ffa600);
        color: #000;
      }
      .table-wrap {
        overflow-x: auto;
      }
      td.num,
      th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
      }
      .mono {
        font-family: var(--ha-font-family-code, monospace);
        font-size: 12px;
      }
      .match {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 100px;
      }
      .match.failing {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      .match.healthy {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      .match.other {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        color: var(--secondary-text-color);
      }
      .chips {
        display: inline-flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .chip {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        border-radius: 100px;
        padding: 2px 8px;
        font-size: 11px;
      }
      .badge-custom {
        display: inline-block;
        margin-left: 6px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        padding: 1px 7px;
        border-radius: 100px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.15);
        color: var(--primary-color);
        vertical-align: middle;
      }
      .sub {
        display: block;
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .note {
        font-size: 11.5px;
        color: var(--secondary-text-color);
        margin-top: 8px;
        line-height: 1.5;
      }
      .finding {
        display: flex;
        gap: 12px;
        padding: 10px 0;
        border-top: 1px solid var(--divider-color);
      }
      .finding:first-of-type {
        border-top: none;
      }
      .sev {
        flex: 0 0 auto;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-top: 6px;
      }
      .sev.high {
        background: var(--status-critical, #d03b3b);
      }
      .sev.medium {
        background: var(--status-warning, #fab219);
      }
      .sev.info {
        background: var(--cat-other, #9aa0a6);
      }
      .finding-title {
        font-weight: 600;
        font-size: 13.5px;
      }
      .finding-detail {
        font-size: 12.5px;
        color: var(--secondary-text-color);
        margin-top: 3px;
        line-height: 1.5;
      }
      .stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 4px;
      }
      .stat-tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .stat-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--secondary-text-color);
      }
      .stat-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.1;
      }
      .domain-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12.5px;
        max-height: 220px;
        overflow-y: auto;
      }
      .domain-list .row {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 3px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .domain-list .row:last-child {
        border-bottom: none;
      }
      .view-toggle {
        display: inline-flex;
        border: 1px solid var(--divider-color);
        border-radius: 100px;
        overflow: hidden;
        margin-bottom: 10px;
      }
      .view-toggle button {
        border: none;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
        font-size: 12px;
        font-weight: 600;
        padding: 5px 14px;
        cursor: pointer;
      }
      .view-toggle button.active {
        background: var(--primary-color);
        color: #fff;
      }
      .device-chip {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.1);
        color: var(--primary-color);
        border: none;
        border-radius: 100px;
        padding: 1px 8px;
        font-size: 10.5px;
        cursor: pointer;
        margin: 2px 3px 0 0;
      }
      .device-chip:hover {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.2);
      }
      .matrix-wrap {
        overflow-x: auto;
      }
      table.zone-matrix {
        border-collapse: collapse;
      }
      table.zone-matrix th,
      table.zone-matrix td {
        border: 1px solid var(--divider-color);
        padding: 6px;
        text-align: center;
        font-size: 11.5px;
      }
      table.zone-matrix th {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.03);
        font-weight: 600;
      }
      table.zone-matrix th.corner {
        background: transparent;
        border: none;
      }
      table.zone-matrix td.cell {
        cursor: pointer;
        min-width: 64px;
      }
      table.zone-matrix td.cell:hover {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      table.zone-matrix td.cell.allow {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      table.zone-matrix td.cell.block {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      table.zone-matrix td.cell.mixed {
        background: rgba(var(--status-warning, #fab219), 0.18);
        color: #9a6a00;
      }
      table.zone-matrix td.cell.none {
        color: var(--secondary-text-color);
      }
      .zone-pair-filter {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12.5px;
        margin-bottom: 10px;
      }
    `],e([pe()],Kt.prototype,"_overview",void 0),e([pe()],Kt.prototype,"_loading",void 0),e([pe()],Kt.prototype,"_error",void 0),e([pe()],Kt.prototype,"_aclSort",void 0),e([pe()],Kt.prototype,"_firewallPolicySort",void 0),e([pe()],Kt.prototype,"_portSort",void 0),e([pe()],Kt.prototype,"_fwViewMode",void 0),e([pe()],Kt.prototype,"_fwZonePairFilter",void 0),e([pe()],Kt.prototype,"_suggestionBusy",void 0),e([pe()],Kt.prototype,"_suggestionError",void 0),e([pe()],Kt.prototype,"_ledger",void 0),e([pe()],Kt.prototype,"_ledgerBusy",void 0),e([pe()],Kt.prototype,"_ledgerError",void 0),e([pe()],Kt.prototype,"_isOwner",void 0),e([pe()],Kt.prototype,"_ssh",void 0),e([pe()],Kt.prototype,"_sshHost",void 0),e([pe()],Kt.prototype,"_sshSelected",void 0),e([pe()],Kt.prototype,"_sshRun",void 0),e([pe()],Kt.prototype,"_sshBusy",void 0),e([pe()],Kt.prototype,"_sshError",void 0),Kt=e([he("ha-soc-network-security-view")],Kt);const Vt=async e=>{const t=(new TextEncoder).encode(e),s=await crypto.subtle.digest("SHA-256",t);return Array.from(new Uint8Array(s)).map(e=>e.toString(16).padStart(2,"0")).join("")},jt=e=>(new TextEncoder).encode(e).length,qt=e=>e?e.split("\n").length:0,Yt=async e=>{try{return void await navigator.clipboard.writeText(e)}catch{}const t=document.createElement("textarea");t.value=e,t.style.position="fixed",t.style.opacity="0",document.body.appendChild(t),t.focus(),t.select();try{document.execCommand("copy")}finally{document.body.removeChild(t)}},Gt=(e,t)=>{const s=new Blob([e],{type:"text/plain;charset=utf-8"}),i=URL.createObjectURL(s),r=document.createElement("a");r.href=i,r.download=t,document.body.appendChild(r),r.click(),document.body.removeChild(r),URL.revokeObjectURL(i)},Xt=()=>(new Date).toISOString().replace(/:/g,"-").replace(/\.\d+Z$/,"Z");var Jt;function Zt(e){const t=e.match(/^homeassistant\.components\.([^.]+)/);if(t)return t[1];const s=e.match(/^custom_components\.([^.]+)/);return s?s[1]:e.split(".")[0]}const Qt=["DEBUG","INFO","WARNING","ERROR","CRITICAL"];function es(e){const t=e.toUpperCase();return Qt.includes(t)?t.toLowerCase():"info"}const ts="system",ss="syslog_receiver";let is=Jt=class extends Je{constructor(){super(...arguments),this._entries=[],this._fault=null,this._loading=!0,this._error=null,this._domainFilter="",this._levelFilter="",this._expanded=new Set,this._sort=null,this._targets=null,this._source=ts,this._containerLog=null,this._boots=[0],this._boot=0,this._containerLoading=!1,this._logFeedback=null,this._syslogEntries=[],this._syslogTotal=0,this._syslogLoading=!1,this._syslogError=null,this._syslogHostFilter="",this._syslogSeverityFilter="",this._syslogSort=null}get viewId(){return"logs"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{const[t,s,i,r]=await Promise.all([(e=this.hass,we(e,{type:"system_log/list"})),Re(this.hass),Pe(this.hass).catch(()=>null),Ae(this.hass).catch(()=>null)]);this._entries=t,this._fault=s,this._targets=i,this._boots=r?.available&&r.boots.length?r.boots:[0]}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}var e}async _loadContainer(e){this._containerLoading=!0;try{this._containerLog=await((e,t,s=0)=>we(e,{type:"ha_soc/logs/container",target:t,boot:s}))(this.hass,e,this._boot)}catch(t){this._containerLog={available:!1,target:e,boot:this._boot,content:null,truncated:!1,error:String(t),fetched_at:(new Date).toISOString()}}finally{this._containerLoading=!1}}async _loadSyslogReceiver(){this._syslogLoading=!0,this._syslogError=null;try{const t=await(e=this.hass,we(e,{type:"ha_soc/syslog_receiver/entries"}));this._syslogEntries=t.entries,this._syslogTotal=t.total}catch(e){this._syslogError=e?.message??String(e)}finally{this._syslogLoading=!1}var e}_onSourceChange(e){const t=e.target.value;this._source=t,this._containerLog=null,t===ss?this._loadSyslogReceiver():t!==ts&&this._loadContainer(t)}_onBootChange(e){this._boot=Number(e.target.value)||0,this._containerLog=null,this._source!==ts&&this._source!==ss&&this._loadContainer(this._source)}_bootLabel(e){return 0===e?"Current boot":-1===e?"Previous boot (-1)":`${-e} boots ago (${e})`}_refresh(){this._source===ts?this._load():this._source===ss?this._loadSyslogReceiver():this._loadContainer(this._source)}get _syslogHosts(){return Array.from(new Set(this._syslogEntries.map(e=>e.hostname??"(unknown)"))).sort()}get _syslogFiltered(){const e=this._syslogEntries.filter(e=>(!this._syslogHostFilter||(e.hostname??"(unknown)")===this._syslogHostFilter)&&(!this._syslogSeverityFilter||e.severity_name===this._syslogSeverityFilter));return Ze(e,this._syslogSort,Jt.SYSLOG_SORT)}_toggleExpanded(e){const t=new Set(this._expanded);t.has(e)?t.delete(e):t.add(e),this._expanded=t}get _domains(){return Array.from(new Set(this._entries.map(e=>Zt(e.name)))).sort()}get _levels(){const e=new Set(this._entries.map(e=>e.level.toUpperCase()));return Qt.filter(t=>e.has(t))}get _filtered(){const e=this._entries.filter(e=>(!this._domainFilter||Zt(e.name)===this._domainFilter)&&(!this._levelFilter||e.level.toUpperCase()===this._levelFilter));return Ze(e,this._sort,Jt.LOG_SORT)}_renderFaultLogCard(){const e=this._fault;return e?K`
      <div class="card fault-log">
        <h3>
          Home Assistant Crash Log
          ${e.exists&&e.content?.trim()?K`<span class="log-level critical"><span class="dot"></span>crash detected</span>`:K`<span class="tag enforced">none detected</span>`}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <code>home-assistant.log.fault</code> — Python's own faulthandler dump. This
          file is only ever written when Home Assistant Core itself crashes at a fatal,
          low level (segfault, abort, illegal instruction) — a normal Python exception
          never creates it, and it's separate from the WARNING/ERROR table below. Home
          Assistant appends to this file across restarts and only deletes it automatically
          after a clean run finds it empty, so old content can persist here until it's
          cleared by hand on the host — this view is read-only and never touches the file.
        </p>
        ${e.exists&&e.content?.trim()?K`
              <p class="muted" style="font-size:12px;">
                Last written ${new Date(e.modified_at).toLocaleString()} —
                ${e.size_bytes.toLocaleString()} byte(s) total${e.truncated?", showing the most recent 64 KB":""}.
              </p>
              <pre>${e.content}</pre>
            `:K`<div class="empty">No crash detected.</div>`}
      </div>
    `:j}async _copyOrDownloadLog(e,t){const s=this._containerLog?.content??"";if(!s)return;const i=qt(s),r=jt(s);try{"copy"===e?await Yt(s):Gt(s,`${t}-${Xt()}.log`)}catch(e){return void(this._error=e.message??String(e))}this._logFeedback=`${"copy"===e?"Copied":"Downloaded"} ${i} line(s)`,window.clearTimeout(this._logFeedbackTimer),this._logFeedbackTimer=window.setTimeout(()=>{this._logFeedback=null},3e3);try{const t=await Vt(s);await je(this.hass,"copy"===e?"copy_logs":"download_logs",i,r,t)}catch{this._logFeedback+=" (audit record failed)"}}_renderContainerLog(){const e=this._containerLog,t=this._targets?.targets.find(e=>e.id===this._source)?.name??this._source;return this._containerLoading&&!e?K`<div class="empty">Loading ${t} logs…</div>`:e?e.available?K`
      <p class="muted" style="font-size:12px;">
        ${this._bootLabel(e.boot??0)}, fetched ${new Date(e.fetched_at).toLocaleString()}${e.truncated?", showing the most recent 128 KB":""}.
        ${e.boot?K`The last lines of an earlier boot are what the host wrote before it
              stopped; a boot that ends without a shutdown message ended uncleanly.`:K`This is the container's live journald stream via Supervisor, point-in-time,
              use Refresh for new lines.`}
      </p>
      <div class="export-row" style="display:flex;gap:8px;align-items:center;margin-bottom:6px;">
        <button class="ha-btn" @click=${()=>this._copyOrDownloadLog("copy",t)}>Copy</button>
        <button class="ha-btn" @click=${()=>this._copyOrDownloadLog("download",t)}>Download</button>
        ${this._logFeedback?K`<span class="muted">${this._logFeedback}</span>`:j}
      </div>
      <pre class="rawlog">${e.content?.trim()?e.content:"(log is empty)"}</pre>
    `:K`<div class="empty">
        Couldn't load ${t} logs${e.error?K`<br /><span class="muted">${e.error}</span>`:j}
      </div>`:K`<div class="empty">Select a source.</div>`}_renderSyslogReceiver(){const e=this._syslogSort,t=e=>{this._syslogSort=e};if(this._syslogLoading&&!this._syslogEntries.length)return K`<div class="empty">Loading…</div>`;if(this._syslogError)return K`
        <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
          <p style="font-size:13px;margin:0 0 8px;">${this._syslogError}</p>
          <button class="ha-btn" @click=${()=>this._loadSyslogReceiver()}>Retry</button>
        </div>
      `;const s=this._syslogFiltered;return s.length?K`
      <p class="muted" style="font-size:12px;">
        Showing the most recent ${this._syslogEntries.length} of ${this._syslogTotal} buffered
        entries (most recent first).
      </p>
      <table>
        <thead>
          <tr>
            ${Qe("Time","time",e,t)}
            ${Qe("Hostname","hostname",e,t)}
            ${Qe("App / Tag","app_name",e,t)}
            ${Qe("Severity","severity",e,t)}
            ${Qe("Message","message",e,t)}
          </tr>
        </thead>
        <tbody>
          ${s.map(e=>K`
              <tr>
                <td>${new Date(e.timestamp).toLocaleString()}</td>
                <td class="muted">${e.hostname??"(unknown)"}</td>
                <td class="muted">${e.app_name??"-"}</td>
                <td>
                  ${e.severity_name?K`<span class="log-level ${es(e.severity_name.toUpperCase())}"
                        ><span class="dot"></span>${e.severity_name}</span
                      >`:K`<span class="muted">-</span>`}
                </td>
                <td>${e.message}${e.raw?K`<span class="muted"> (unparsed)</span>`:j}</td>
              </tr>
            `)}
        </tbody>
      </table>
    `:K`<div class="empty">No forwarded log entries received yet.</div>`}render(){const e=this._filtered,t=this._sort,s=e=>{this._sort=e,this._expanded=new Set},i=this._source===ts,r=this._source===ss,n=[{id:"fault_log",title:"Home Assistant Crash Log",render:()=>this._renderFaultLogCard()},{id:"logs",title:"Logs",hideable:!1,render:()=>K`
      <div class="card">
        <h3>Logs</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          ${i?K`The same WARNING/ERROR/CRITICAL buffer as Settings → System → Logs
                (<code>/config/logs</code>), deduplicated, most recent first. This shows Home
                Assistant's own captured log records only. For an app or add-on's full
                container output, pick it from the source selector.`:r?K`Container logs forwarded to HA SOC's syslog receiver (e.g. by the
                "logspout" HA add-on), which forwards every Docker container's
                stdout/stderr over syslog+udp — a continuously-growing feed, most
                recent first. Configure the receiver in Settings → SIEM / Syslog Export.`:K`Raw container output captured by the Supervisor, the same stream as the
                add-on's own Log tab. ANSI colors are stripped server-side.`}
        </p>
        <div class="toolbar">
          ${this._targets?.available?K`
                <select @change=${this._onSourceChange} aria-label="Log source">
                  <option value=${ts} ?selected=${i}>
                    Integration logs (captured records)
                  </option>
                  <option value=${ss} ?selected=${r}>
                    Forwarded container logs (logspout)
                  </option>
                  ${this._targets.targets.map(e=>K`<option value=${e.id} ?selected=${e.id===this._source}>${e.name}</option>`)}
                </select>
                ${!i&&!r&&this._boots.length>1?K`
                      <select @change=${this._onBootChange} aria-label="Boot" title="Which boot's journal to read">
                        ${this._boots.map(e=>K`<option value=${e} ?selected=${e===this._boot}>${this._bootLabel(e)}</option>`)}
                      </select>
                    `:j}
              `:j}
          ${i?K`
                <select
                  aria-label="Filter by integration"
                  @change=${e=>{this._domainFilter=e.target.value,this._expanded=new Set}}
                >
                  <option value="" ?selected=${""===this._domainFilter}>All integrations</option>
                  ${this._domains.map(e=>K`<option value=${e} ?selected=${e===this._domainFilter}>${e}</option>`)}
                </select>
                <select
                  aria-label="Filter by level"
                  @change=${e=>{this._levelFilter=e.target.value,this._expanded=new Set}}
                >
                  <option value="" ?selected=${""===this._levelFilter}>All levels</option>
                  ${this._levels.map(e=>K`<option value=${e} ?selected=${e===this._levelFilter}>${e}</option>`)}
                </select>
              `:j}
          ${r?K`
                <select
                  aria-label="Filter by hostname"
                  @change=${e=>{this._syslogHostFilter=e.target.value}}
                >
                  <option value="" ?selected=${""===this._syslogHostFilter}>All hostnames</option>
                  ${this._syslogHosts.map(e=>K`<option value=${e} ?selected=${e===this._syslogHostFilter}>${e}</option>`)}
                </select>
                <select
                  aria-label="Filter by severity"
                  @change=${e=>{this._syslogSeverityFilter=e.target.value}}
                >
                  <option value="" ?selected=${""===this._syslogSeverityFilter}>All severities</option>
                  ${["emerg","alert","crit","err","warning","notice","info","debug"].map(e=>K`<option value=${e} ?selected=${e===this._syslogSeverityFilter}>${e}</option>`)}
                </select>
              `:j}
          <span class="spacer"></span>
          <button
            class="ha-btn"
            @click=${this._refresh}
            ?disabled=${this._containerLoading||this._syslogLoading}
          >
            ${this._containerLoading||this._syslogLoading?"Loading…":"Refresh"}
          </button>
        </div>
        ${r?this._renderSyslogReceiver():i?this._loading?K`<div class="empty">Loading…</div>`:this._error?K`
              <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
                <p style="font-size:13px;margin:0 0 8px;">${this._error}</p>
                <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
              </div>
            `:e.length?K`
              <table>
                <thead>
                  <tr>
                    ${Qe("Time","time",t,s)}
                    ${Qe("Level","level",t,s)}
                    ${Qe("Integration","integration",t,s)}
                    ${Qe("Message","message",t,s)}
                    ${Qe("Count","count",t,s,{numeric:!0})}
                  </tr>
                </thead>
                <tbody>
                  ${e.map((e,t)=>{const s=this._expanded.has(t);return K`
                      <tr
                        class=${e.exception?"clickable":""}
                        title=${e.exception?"Click to show/hide the traceback":""}
                        @click=${()=>e.exception&&this._toggleExpanded(t)}
                      >
                        <td>${new Date(1e3*e.first_occurred).toLocaleString()}</td>
                        <td>
                          <span class="log-level ${es(e.level)}"
                            ><span class="dot"></span>${e.level}</span
                          >
                        </td>
                        <td class="muted">${Zt(e.name)}</td>
                        <td>
                          ${e.message[e.message.length-1]}
                          ${e.source?K`<div class="muted" style="font-size:11px;">${e.source[0]}:${e.source[1]}</div>`:j}
                        </td>
                        <td class="num">${e.count}</td>
                      </tr>
                      ${s&&e.exception?K`
                            <tr>
                              <td colspan="5">
                                <pre
                                  style="white-space:pre-wrap;font-size:11.5px;background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);padding:10px;border-radius:6px;margin:0;"
                                >
${e.exception}</pre
                                >
                              </td>
                            </tr>
                          `:j}
                    `})}
                </tbody>
              </table>
            `:K`<div class="empty">No matching log entries.</div>`:this._renderContainerLog()}
      </div>
        `}];return this._renderSections(n)}};var rs;is.styles=[qe,a`
      .log-level {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.02em;
        padding: 3px 8px;
        border-radius: 100px;
      }
      .log-level .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        flex: none;
      }
      .log-level.debug {
        background: rgba(154, 160, 166, 0.16);
        color: var(--secondary-text-color);
      }
      .log-level.debug .dot {
        background: var(--cat-other, #9aa0a6);
      }
      .log-level.info {
        background: rgba(42, 120, 214, 0.14);
        color: var(--cat-1, #2a78d6);
      }
      .log-level.info .dot {
        background: var(--cat-1, #2a78d6);
      }
      .log-level.warning {
        background: rgba(250, 178, 25, 0.16);
        color: #7a5200;
      }
      .log-level.warning .dot {
        background: var(--status-warning, #fab219);
      }
      .log-level.error {
        background: rgba(236, 131, 90, 0.18);
        color: var(--status-serious, #ec835a);
      }
      .log-level.error .dot {
        background: var(--status-serious, #ec835a);
      }
      .log-level.critical {
        background: rgba(208, 59, 59, 0.18);
        color: var(--status-critical, #d03b3b);
      }
      .log-level.critical .dot {
        background: var(--status-critical, #d03b3b);
      }
      :host(.dark) .log-level.warning {
        color: var(--status-warning, #fab219);
      }
      .fault-log pre,
      .rawlog {
        white-space: pre-wrap;
        font-size: 11.5px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
        padding: 10px;
        border-radius: 6px;
        margin: 0;
        max-height: 400px;
        overflow-y: auto;
      }
      .rawlog {
        max-height: 600px;
        font-family: var(--ha-font-family-code, monospace);
      }
    `],is.SYSLOG_SORT={time:e=>e.timestamp,hostname:e=>e.hostname??"",app_name:e=>e.app_name??"",severity:e=>e.severity??99,message:e=>e.message},is.LOG_SORT={time:e=>e.first_occurred,level:e=>{const t=Qt.indexOf(e.level.toUpperCase());return-1===t?null:t},integration:e=>Zt(e.name),message:e=>e.message[e.message.length-1],count:e=>e.count},e([pe()],is.prototype,"_entries",void 0),e([pe()],is.prototype,"_fault",void 0),e([pe()],is.prototype,"_loading",void 0),e([pe()],is.prototype,"_error",void 0),e([pe()],is.prototype,"_domainFilter",void 0),e([pe()],is.prototype,"_levelFilter",void 0),e([pe()],is.prototype,"_expanded",void 0),e([pe()],is.prototype,"_sort",void 0),e([pe()],is.prototype,"_targets",void 0),e([pe()],is.prototype,"_source",void 0),e([pe()],is.prototype,"_containerLog",void 0),e([pe()],is.prototype,"_boots",void 0),e([pe()],is.prototype,"_boot",void 0),e([pe()],is.prototype,"_containerLoading",void 0),e([pe()],is.prototype,"_logFeedback",void 0),e([pe()],is.prototype,"_syslogEntries",void 0),e([pe()],is.prototype,"_syslogTotal",void 0),e([pe()],is.prototype,"_syslogLoading",void 0),e([pe()],is.prototype,"_syslogError",void 0),e([pe()],is.prototype,"_syslogHostFilter",void 0),e([pe()],is.prototype,"_syslogSeverityFilter",void 0),e([pe()],is.prototype,"_syslogSort",void 0),is=Jt=e([he("ha-soc-logs-view")],is);let ns=rs=class extends Je{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._error=null,this._busyKey=null,this._showIgnored=!1,this._sort=null,this._ignoredSort=null}get viewId(){return"peripherals"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{this._overview=await Ie(this.hass)}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}}async _onToggleIgnore(e,t,s){this._busyKey=e;try{await((e,t,s,i)=>we(e,{type:"ha_soc/peripherals/set_ignored",key:t,ignored:s,raw_name:i}))(this.hass,e,t,s),await this._load()}finally{this._busyKey=null}}render(){if(this._loading)return K`<div class="empty">Loading peripherals…</div>`;if(this._error)return K`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Local Peripherals</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const e=this._overview;if(!e||!e.available)return K`
        <div class="card">
          <h3>Local Peripherals</h3>
          <p class="muted" style="font-size:12.5px;">
            Home Assistant's own USB discovery component (<code>usb</code>) isn't
            available — it's part of every default install, so this usually only
            happens if it's been explicitly disabled. This view has nothing to read
            without it.
          </p>
        </div>
      `;const t=e.devices.filter(e=>!e.ignored),s=e.devices.filter(e=>e.ignored),i=[{id:"peripherals",title:"Local Peripherals",hideable:!1,render:()=>K`
      <div class="card">
        <h3>Local Peripherals</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          USB serial devices Home Assistant itself can see — the same discovery data
          core uses to auto-detect a Zigbee/Z-Wave USB stick, so no add-on is involved.
          This only covers serial (<code>/dev/ttyUSB*</code>/<code>/dev/ttyACM*</code>)
          devices, not every USB peripheral. "Assigned integration" is a best-effort
          match against every config entry's stored data — a miss doesn't prove a
          device is unused, only that this couldn't find it.
        </p>
        ${e.devices.length?K`
              <table>
                <thead>
                  <tr>
                    ${Qe("Raw Name","name",this._sort,e=>this._sort=e)}
                    ${Qe("/dev/tty Path","tty",this._sort,e=>this._sort=e)}
                    ${Qe("By-ID Path","by_id",this._sort,e=>this._sort=e)}
                    ${Qe("VID:PID","vidpid",this._sort,e=>this._sort=e)}
                    ${Qe("Serial","serial",this._sort,e=>this._sort=e)}
                    ${Qe("Assigned Integration","integration",this._sort,e=>this._sort=e)}
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${Ze(t,this._sort,rs.DEVICE_SORT).map(e=>K`
                      <tr>
                        <td>${e.raw_name}</td>
                        <td class="muted">${e.tty_path}</td>
                        <td class="muted" style="font-size:12px;word-break:break-all;">
                          ${e.by_id_path??"—"}
                        </td>
                        <td class="muted" style="font-size:12px;">${e.vid}:${e.pid}</td>
                        <td class="muted" style="font-size:12px;">${e.serial_number??"—"}</td>
                        <td>
                          ${e.assigned_integration?K`${e.assigned_integration.title}
                                <span class="muted">(${e.assigned_integration.domain})</span>`:K`<span class="pill medium"><span class="dot"></span>unassigned</span>`}
                        </td>
                        <td>
                          ${e.assigned_integration?j:K`
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey===e.key}
                                  @click=${()=>this._onToggleIgnore(e.key,!0,e.raw_name)}
                                >
                                  Ignore
                                </button>
                              `}
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:K`<div class="empty">
              No USB serial devices detected. If you're expecting one here, confirm
              Home Assistant actually has access to it — automatic on Home Assistant
              OS for devices your system exposes; a Container/Core install needs the
              device passed through explicitly (e.g. Docker's <code>--device</code>).
            </div>`}
      </div>
        `},{id:"ignored_peripherals",title:"Ignored Peripherals",render:()=>s.length?K`
            <div class="card">
              <h3 style="cursor:pointer;" @click=${()=>this._showIgnored=!this._showIgnored}>
                Ignored (${s.length}) ${this._showIgnored?"▲":"▼"}
              </h3>
              ${this._showIgnored?K`
                    <table>
                      <thead>
                        <tr>
                          ${Qe("Raw Name","name",this._ignoredSort,e=>this._ignoredSort=e)}
                          ${Qe("/dev/tty Path","tty",this._ignoredSort,e=>this._ignoredSort=e)}
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        ${Ze(s,this._ignoredSort,rs.DEVICE_SORT).map(e=>K`
                            <tr class="row-disabled">
                              <td>${e.raw_name}</td>
                              <td class="muted">${e.tty_path}</td>
                              <td>
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey===e.key}
                                  @click=${()=>this._onToggleIgnore(e.key,!1,e.raw_name)}
                                >
                                  Un-ignore
                                </button>
                              </td>
                            </tr>
                          `)}
                      </tbody>
                    </table>
                  `:j}
            </div>
          `:j}];return this._renderSections(i)}};var os;ns.styles=qe,ns.DEVICE_SORT={name:e=>e.raw_name,tty:e=>e.tty_path,by_id:e=>e.by_id_path,vidpid:e=>`${e.vid}:${e.pid}`,serial:e=>e.serial_number,integration:e=>e.assigned_integration?.title??null},e([pe()],ns.prototype,"_overview",void 0),e([pe()],ns.prototype,"_loading",void 0),e([pe()],ns.prototype,"_error",void 0),e([pe()],ns.prototype,"_busyKey",void 0),e([pe()],ns.prototype,"_showIgnored",void 0),e([pe()],ns.prototype,"_sort",void 0),e([pe()],ns.prototype,"_ignoredSort",void 0),ns=rs=e([he("ha-soc-peripherals-view")],ns);const as={automation:"Automations",script:"Scripts",scene:"Scenes",dashboard:"Views (dashboards)",helper:"Helpers",other:"Other (review manually)"};let ls=os=class extends Je{constructor(){super(...arguments),this._entities=[],this._oldEntityId="",this._newEntityId="",this._report=null,this._finding=!1,this._applying=!1,this._applyResult=null,this._backupAck=!1,this._applyError=null,this._broken=[],this._brokenLoading=!0,this._brokenError=null,this._brokenFilter=null,this._brokenSort=null,this._isOwner=!1,this._filterSameType=!0}get viewId(){return"entity_remap"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._brokenLoading=!0,this._brokenError=null;try{const[t,s,i]=await Promise.all([(e=this.hass,we(e,{type:"config/entity_registry/list"})),Ne(this.hass),Me(this.hass).catch(()=>({is_owner:!1}))]);this._entities=t,this._broken=s,this._isOwner=!!i.is_owner}catch(e){this._brokenError=e?.message??String(e)}finally{this._brokenLoading=!1}var e}_labelFor(e){const t=this._entities.find(t=>t.entity_id===e),s=t?.name||t?.original_name;return s?`${s} (${e})`:e}async _onFind(){if(this._oldEntityId){this._finding=!0,this._applyResult=null,this._applyError=null;try{this._report=await(e=this.hass,t=this._oldEntityId,we(e,{type:"ha_soc/entity_remap/find_references",entity_id:t})),this._brokenFilter=this._oldEntityId}finally{this._finding=!1}var e,t}}_onFixBroken(e){this._oldEntityId=e,this._newEntityId="",this._report=null,this._applyResult=null,this._applyError=null,this._onFind()}_selectOld(e){this._oldEntityId=e,this._newEntityId="",this._report=null,this._applyResult=null,this._applyError=null,this.updateComplete.then(()=>{this.renderRoot?.querySelector("#remap-card")?.scrollIntoView({behavior:"smooth",block:"start"})})}_domainOf(e){return e.includes(".")?e.split(".",1)[0]:""}_newEntityOptions(){const e=this._domainOf(this._oldEntityId);return this._filterSameType&&e?this._entities.filter(t=>this._domainOf(t.entity_id)===e):this._entities}_onClearBrokenFilter(){this._brokenFilter=null}_filteredBroken(){return this._brokenFilter?this._broken.filter(e=>e.entity_id===this._brokenFilter):this._broken}async _onApply(){if(this._oldEntityId&&this._newEntityId){this._applying=!0,this._applyError=null;try{const r=await(e=this.hass,t=this._oldEntityId,s=this._newEntityId,i=this._backupAck,we(e,{type:"ha_soc/entity_remap/apply",old_entity_id:t,new_entity_id:s,backup_acknowledged:i}));this._backupAck=!1,await this._onFind(),this._broken=await Ne(this.hass),this._applyResult=r}catch(e){this._applyError=e?.message??e?.code??"Applying the remap failed."}finally{this._applying=!1}var e,t,s,i}}_renderKind(e,t){return t.length?K`
      <div style="margin-bottom:12px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          ${as[e]??e} (${t.length})
        </div>
        <table>
          <tbody>
            ${t.map(e=>K`
                <tr>
                  <td>${e.name}</td>
                  <td>
                    <span class="tag ${e.editable?"enforced":"cosmetic"}">
                      ${e.editable?"will fix":"manual review"}
                    </span>
                  </td>
                  <td class="muted" style="font-size:12px;">${e.reason??""}</td>
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `:j}render(){const e=this._report,t=!!e&&e.editable_count>0&&!!this._newEntityId&&this._newEntityId!==this._oldEntityId&&this._backupAck,s=[{id:"entity_remap",title:"Entity ReMap",hideable:!1,render:()=>K`
      <div class="card" id="remap-card">
        <h3>Entity ReMap</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant has no built-in way to do this: renaming or replacing an entity
          only ever touches the entity registry — every automation, script, scene,
          dashboard, and helper that still references the old entity_id keeps that exact
          string and silently breaks. Pick the broken/old entity and its replacement below
          to find every reference and fix the ones that are safely, structurally editable.
          A reference that only exists inside a template (<code>{{ states('...') }}</code>)
          is never rewritten automatically — it's flagged for you to fix by hand instead,
          since a text rewrite there risks corrupting the template or missing a dynamic
          reference.
        </p>

        <div class="toolbar" style="align-items:flex-end;">
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">Old / broken entity</div>
            <input
              list="ha-soc-remap-old-entities"
              style="width:320px;"
              .value=${this._oldEntityId}
              placeholder="sensor.old_entity_id"
              @change=${e=>this._oldEntityId=e.target.value.trim()}
            />
          </div>
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">New / replacement entity</div>
            <input
              list="ha-soc-remap-new-entities"
              style="width:320px;"
              .value=${this._newEntityId}
              placeholder="sensor.new_entity_id"
              @change=${e=>this._newEntityId=e.target.value.trim()}
            />
          </div>
          <button class="ha-btn" ?disabled=${!this._oldEntityId||this._finding} @click=${()=>this._onFind()}>
            ${this._finding?"Searching…":"Find references"}
          </button>
          <label
            class="muted"
            style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;"
            title="Only suggest replacement entities in the same domain (binary_sensor, sensor, weather, …) as the old entity"
          >
            <input
              type="checkbox"
              .checked=${this._filterSameType}
              @change=${e=>this._filterSameType=e.target.checked}
            />
            Filter by same Entity Type
          </label>
          <!-- Old/broken entity only offers entities this page already knows are
               referenced-but-missing — picking from the full entity registry made
               no sense here, since a genuinely broken entity isn't in it. -->
          <datalist id="ha-soc-remap-old-entities">
            ${this._broken.map(e=>K`<option value=${e.entity_id}>${this._labelFor(e.entity_id)}</option>`)}
          </datalist>
          <!-- New/replacement entity picks from currently-registered entities,
               constrained to the old entity's domain when the checkbox is on. -->
          <datalist id="ha-soc-remap-new-entities">
            ${this._newEntityOptions().map(e=>K`<option value=${e.entity_id}>${e.name??e.original_name??""}</option>`)}
          </datalist>
        </div>

        ${e?K`
              <div style="margin-top:12px;">
                ${0===e.total_count?K`<div class="empty">No references to ${e.entity_id} found anywhere.</div>`:K`
                      <p class="muted" style="font-size:12.5px;">
                        ${e.total_count} reference(s) found — ${e.editable_count} can be fixed
                        automatically, the rest need a manual look.
                      </p>
                      ${this._renderKind("automation",e.automation)}
                      ${this._renderKind("script",e.script)}
                      ${this._renderKind("scene",e.scene)}
                      ${this._renderKind("dashboard",e.dashboard)}
                      ${this._renderKind("helper",e.helper)}
                      ${this._renderKind("other",e.other)}
                    `}
                ${this._isOwner?K`
                      ${e.editable_count>0?K`
                            <!-- The server refuses the apply without backup_acknowledged, so this
                                 checkbox is the same required gate the firewall card's backup
                                 acknowledgment is, with the consequences spelled out honestly. -->
                            <label
                              style="display:flex;align-items:flex-start;gap:8px;font-size:12.5px;margin-top:12px;cursor:pointer;"
                            >
                              <input
                                type="checkbox"
                                style="margin-top:2px;"
                                .checked=${this._backupAck}
                                @change=${e=>this._backupAck=e.target.checked}
                              />
                              <span>
                                I understand that before their first rewrite,
                                <code>automations.yaml</code>, <code>scripts.yaml</code>, and
                                <code>scenes.yaml</code> are each copied aside as
                                <code>&lt;file&gt;.ha_soc-&lt;timestamp&gt;.bak</code>; that
                                storage-mode dashboards and helper entries get a JSON snapshot of
                                their previous state under <code>.storage/ha_soc_remap/</code>
                                (kept for 30 days) before being rewritten in place; that a YAML
                                file containing <code>!secret</code> or <code>!include</code> is
                                refused entirely and reported as "manual edit required"; that
                                comments and formatting in the YAML files do not survive the
                                rewrite; and that automations, scripts, and scenes reload right
                                after the write.
                              </span>
                            </label>
                          `:j}
                      <button
                        class="ha-btn"
                        style="margin-top:12px;"
                        ?disabled=${!t||this._applying}
                        @click=${()=>this._onApply()}
                      >
                        ${this._applying?"Applying…":`Apply remap (${e.editable_count} reference${1===e.editable_count?"":"s"})`}
                      </button>
                    `:K`
                      <!-- Applying is owner-only server-side (D-23), so a non-owner
                           admin gets the Settings tab's one-line note instead of an
                           apply button that could only ever bounce off the gate. -->
                      <p class="muted" style="font-size:12.5px;margin-top:12px;">
                        Applying a remap is available to the account owner only.
                      </p>
                    `}
              </div>
            `:j}

        ${this._applyError?K`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">
              Apply failed: ${this._applyError}
            </p>`:j}

        ${this._applyResult?K`
              <div class="card" style="margin-top:12px;background:rgba(67,160,71,0.08);">
                <strong>Applied.</strong> ${Object.entries(this._applyResult.fixed).filter(([,e])=>e>0).map(([e,t])=>`${t} ${as[e]??e}`).join(", ")||"Nothing needed changing."}
                ${this._applyResult.errors.length?K`<div style="color:var(--error-color);margin-top:6px;">
                      ${this._applyResult.errors.length} error(s): ${this._applyResult.errors.join("; ")}
                    </div>`:j}
                ${this._applyResult.backups?.length?K`<div class="muted" style="font-size:12px;margin-top:6px;">
                      Backups written before the rewrite:
                      ${this._applyResult.backups.map(e=>K`<div><code>${e}</code></div>`)}
                    </div>`:j}
              </div>
            `:j}
      </div>
        `},{id:"broken_references",title:"Entities referenced but not found",render:()=>K`
      <div class="card">
        <h3>
          Entities referenced but not found (${this._filteredBroken().length}${this._brokenFilter?K` of ${this._broken.length}`:j})
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A proactive sweep of every automation, script, scene, and structured helper —
          any entity_id they reference that doesn't correspond to a known entity right now.
          Dashboards aren't swept here (there's no equivalent core-provided index to walk
          cheaply); use the search above for a specific entity_id to also cover those.
        </p>
        ${this._brokenFilter?K`
              <div class="toolbar" style="margin-bottom:8px;">
                <span class="muted" style="font-size:12px;">
                  Filtered to <code>${this._brokenFilter}</code>
                </span>
                <button class="ha-btn" @click=${()=>this._onClearBrokenFilter()}>Clear filter</button>
              </div>
            `:j}
        ${this._brokenLoading?K`<div class="empty">Loading…</div>`:this._brokenError?K`
                <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
                  <p style="font-size:13px;margin:0 0 8px;">${this._brokenError}</p>
                  <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
                </div>
              `:this._broken.length?this._filteredBroken().length?K`
                <table>
                  <thead>
                    <tr>
                      ${Qe("Entity ID","entity_id",this._brokenSort,e=>this._brokenSort=e)}
                      ${Qe("Referenced by","referenced_by",this._brokenSort,e=>this._brokenSort=e)}
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${Ze(this._filteredBroken(),this._brokenSort,os.BROKEN_SORT).map(e=>K`
                        <tr>
                          <td>
                            <code
                              style="cursor:pointer;color:var(--primary-color);"
                              title="Select as the Old / broken entity"
                              @click=${()=>this._selectOld(e.entity_id)}
                              >${e.entity_id}</code
                            >
                          </td>
                          <td class="muted" style="font-size:12px;">
                            ${e.referenced_by.map(e=>`${e.name} (${e.kind})`).join(", ")}
                          </td>
                          <td>
                            <button class="ha-btn" @click=${()=>this._onFixBroken(e.entity_id)}>Fix…</button>
                          </td>
                        </tr>
                      `)}
                  </tbody>
                </table>
              `:K`<div class="empty">No broken reference matches <code>${this._brokenFilter}</code>.</div>`:K`<div class="empty">Nothing found — no dangling entity references detected.</div>`}
      </div>
        `}];return this._renderSections(s)}};ls.styles=qe,ls.BROKEN_SORT={entity_id:e=>e.entity_id,referenced_by:e=>e.referenced_by[0]?.name??null},e([pe()],ls.prototype,"_entities",void 0),e([pe()],ls.prototype,"_oldEntityId",void 0),e([pe()],ls.prototype,"_newEntityId",void 0),e([pe()],ls.prototype,"_report",void 0),e([pe()],ls.prototype,"_finding",void 0),e([pe()],ls.prototype,"_applying",void 0),e([pe()],ls.prototype,"_applyResult",void 0),e([pe()],ls.prototype,"_backupAck",void 0),e([pe()],ls.prototype,"_applyError",void 0),e([pe()],ls.prototype,"_broken",void 0),e([pe()],ls.prototype,"_brokenLoading",void 0),e([pe()],ls.prototype,"_brokenError",void 0),e([pe()],ls.prototype,"_brokenFilter",void 0),e([pe()],ls.prototype,"_brokenSort",void 0),e([pe()],ls.prototype,"_isOwner",void 0),e([pe()],ls.prototype,"_filterSameType",void 0),ls=os=e([he("ha-soc-entity-remap-view")],ls);const hs={hours:24,buckets:6,includeHidden:!1},cs=[{id:"device",label:"Devices",color:"#4c9ffe",lane:0},{id:"entity",label:"Entities",color:"#3ddc84",lane:1},{id:"area",label:"Areas",color:"#f3d04e",lane:2},{id:"integration",label:"Integrations",color:"#b45cf0",lane:3}],ds=[{id:"device_entity",label:"Device hosts entity",color:"#3ddc84"},{id:"device_area",label:"Device in area",color:"#f3d04e"},{id:"entity_area",label:"Entity in area",color:"#e4a33c"},{id:"integration_device",label:"Integration provides device",color:"#b45cf0"},{id:"integration_entity",label:"Integration provides entity",color:"#c58cff"},{id:"via_device",label:"Connected through device",color:"#ff7a5c"}],us=e=>new Date(e).toISOString();function ps(e,t,s,i){if(isNaN(t)||isNaN(s))return e;var r,n,o,a,l,h,c,d,u,p=e._root,_={data:i},f=e._x0,g=e._y0,v=e._x1,m=e._y1;if(!p)return e._root=_,e;for(;p.length;)if((h=t>=(n=(f+v)/2))?f=n:v=n,(c=s>=(o=(g+m)/2))?g=o:m=o,r=p,!(p=p[d=c<<1|h]))return r[d]=_,e;if(a=+e._x.call(null,p.data),l=+e._y.call(null,p.data),t===a&&s===l)return _.next=p,r?r[d]=_:e._root=_,e;do{r=r?r[d]=new Array(4):e._root=new Array(4),(h=t>=(n=(f+v)/2))?f=n:v=n,(c=s>=(o=(g+m)/2))?g=o:m=o}while((d=c<<1|h)==(u=(l>=o)<<1|a>=n));return r[u]=p,r[d]=_,e}function _s(e,t,s,i,r){this.node=e,this.x0=t,this.y0=s,this.x1=i,this.y1=r}function fs(e){return e[0]}function gs(e){return e[1]}function vs(e,t,s){var i=new ms(null==t?fs:t,null==s?gs:s,NaN,NaN,NaN,NaN);return null==e?i:i.addAll(e)}function ms(e,t,s,i,r,n){this._x=e,this._y=t,this._x0=s,this._y0=i,this._x1=r,this._y1=n,this._root=void 0}function ys(e){for(var t={data:e.data},s=t;e=e.next;)s=s.next={data:e.data};return t}var bs=vs.prototype=ms.prototype;function ws(e){return function(){return e}}function Ss(e){return 1e-6*(e()-.5)}function xs(e){return e.x+e.vx}function $s(e){return e.y+e.vy}function ks(e){var t,s,i,r=1,n=1;function o(){for(var e,o,l,h,c,d,u,p=t.length,_=0;_<n;++_)for(o=vs(t,xs,$s).visitAfter(a),e=0;e<p;++e)l=t[e],d=s[l.index],u=d*d,h=l.x+l.vx,c=l.y+l.vy,o.visit(f);function f(e,t,s,n,o){var a=e.data,p=e.r,_=d+p;if(!a)return t>h+_||n<h-_||s>c+_||o<c-_;if(a.index>l.index){var f=h-a.x-a.vx,g=c-a.y-a.vy,v=f*f+g*g;v<_*_&&(0===f&&(v+=(f=Ss(i))*f),0===g&&(v+=(g=Ss(i))*g),v=(_-(v=Math.sqrt(v)))/v*r,l.vx+=(f*=v)*(_=(p*=p)/(u+p)),l.vy+=(g*=v)*_,a.vx-=f*(_=1-_),a.vy-=g*_)}}}function a(e){if(e.data)return e.r=s[e.data.index];for(var t=e.r=0;t<4;++t)e[t]&&e[t].r>e.r&&(e.r=e[t].r)}function l(){if(t){var i,r,n=t.length;for(s=new Array(n),i=0;i<n;++i)r=t[i],s[r.index]=+e(r,i,t)}}return"function"!=typeof e&&(e=ws(null==e?1:+e)),o.initialize=function(e,s){t=e,i=s,l()},o.iterations=function(e){return arguments.length?(n=+e,o):n},o.strength=function(e){return arguments.length?(r=+e,o):r},o.radius=function(t){return arguments.length?(e="function"==typeof t?t:ws(+t),l(),o):e},o}function Cs(e){return e.index}function Es(e,t){var s=e.get(t);if(!s)throw new Error("node not found: "+t);return s}function Rs(e){var t,s,i,r,n,o,a=Cs,l=function(e){return 1/Math.min(r[e.source.index],r[e.target.index])},h=ws(30),c=1;function d(i){for(var r=0,a=e.length;r<c;++r)for(var l,h,d,u,p,_,f,g=0;g<a;++g)h=(l=e[g]).source,u=(d=l.target).x+d.vx-h.x-h.vx||Ss(o),p=d.y+d.vy-h.y-h.vy||Ss(o),u*=_=((_=Math.sqrt(u*u+p*p))-s[g])/_*i*t[g],p*=_,d.vx-=u*(f=n[g]),d.vy-=p*f,h.vx+=u*(f=1-f),h.vy+=p*f}function u(){if(i){var o,l,h=i.length,c=e.length,d=new Map(i.map((e,t)=>[a(e,t,i),e]));for(o=0,r=new Array(h);o<c;++o)(l=e[o]).index=o,"object"!=typeof l.source&&(l.source=Es(d,l.source)),"object"!=typeof l.target&&(l.target=Es(d,l.target)),r[l.source.index]=(r[l.source.index]||0)+1,r[l.target.index]=(r[l.target.index]||0)+1;for(o=0,n=new Array(c);o<c;++o)l=e[o],n[o]=r[l.source.index]/(r[l.source.index]+r[l.target.index]);t=new Array(c),p(),s=new Array(c),_()}}function p(){if(i)for(var s=0,r=e.length;s<r;++s)t[s]=+l(e[s],s,e)}function _(){if(i)for(var t=0,r=e.length;t<r;++t)s[t]=+h(e[t],t,e)}return null==e&&(e=[]),d.initialize=function(e,t){i=e,o=t,u()},d.links=function(t){return arguments.length?(e=t,u(),d):e},d.id=function(e){return arguments.length?(a=e,d):a},d.iterations=function(e){return arguments.length?(c=+e,d):c},d.strength=function(e){return arguments.length?(l="function"==typeof e?e:ws(+e),p(),d):l},d.distance=function(e){return arguments.length?(h="function"==typeof e?e:ws(+e),_(),d):h},d}bs.copy=function(){var e,t,s=new ms(this._x,this._y,this._x0,this._y0,this._x1,this._y1),i=this._root;if(!i)return s;if(!i.length)return s._root=ys(i),s;for(e=[{source:i,target:s._root=new Array(4)}];i=e.pop();)for(var r=0;r<4;++r)(t=i.source[r])&&(t.length?e.push({source:t,target:i.target[r]=new Array(4)}):i.target[r]=ys(t));return s},bs.add=function(e){const t=+this._x.call(null,e),s=+this._y.call(null,e);return ps(this.cover(t,s),t,s,e)},bs.addAll=function(e){var t,s,i,r,n=e.length,o=new Array(n),a=new Array(n),l=1/0,h=1/0,c=-1/0,d=-1/0;for(s=0;s<n;++s)isNaN(i=+this._x.call(null,t=e[s]))||isNaN(r=+this._y.call(null,t))||(o[s]=i,a[s]=r,i<l&&(l=i),i>c&&(c=i),r<h&&(h=r),r>d&&(d=r));if(l>c||h>d)return this;for(this.cover(l,h).cover(c,d),s=0;s<n;++s)ps(this,o[s],a[s],e[s]);return this},bs.cover=function(e,t){if(isNaN(e=+e)||isNaN(t=+t))return this;var s=this._x0,i=this._y0,r=this._x1,n=this._y1;if(isNaN(s))r=(s=Math.floor(e))+1,n=(i=Math.floor(t))+1;else{for(var o,a,l=r-s||1,h=this._root;s>e||e>=r||i>t||t>=n;)switch(a=(t<i)<<1|e<s,(o=new Array(4))[a]=h,h=o,l*=2,a){case 0:r=s+l,n=i+l;break;case 1:s=r-l,n=i+l;break;case 2:r=s+l,i=n-l;break;case 3:s=r-l,i=n-l}this._root&&this._root.length&&(this._root=h)}return this._x0=s,this._y0=i,this._x1=r,this._y1=n,this},bs.data=function(){var e=[];return this.visit(function(t){if(!t.length)do{e.push(t.data)}while(t=t.next)}),e},bs.extent=function(e){return arguments.length?this.cover(+e[0][0],+e[0][1]).cover(+e[1][0],+e[1][1]):isNaN(this._x0)?void 0:[[this._x0,this._y0],[this._x1,this._y1]]},bs.find=function(e,t,s){var i,r,n,o,a,l,h,c=this._x0,d=this._y0,u=this._x1,p=this._y1,_=[],f=this._root;for(f&&_.push(new _s(f,c,d,u,p)),null==s?s=1/0:(c=e-s,d=t-s,u=e+s,p=t+s,s*=s);l=_.pop();)if(!(!(f=l.node)||(r=l.x0)>u||(n=l.y0)>p||(o=l.x1)<c||(a=l.y1)<d))if(f.length){var g=(r+o)/2,v=(n+a)/2;_.push(new _s(f[3],g,v,o,a),new _s(f[2],r,v,g,a),new _s(f[1],g,n,o,v),new _s(f[0],r,n,g,v)),(h=(t>=v)<<1|e>=g)&&(l=_[_.length-1],_[_.length-1]=_[_.length-1-h],_[_.length-1-h]=l)}else{var m=e-+this._x.call(null,f.data),y=t-+this._y.call(null,f.data),b=m*m+y*y;if(b<s){var w=Math.sqrt(s=b);c=e-w,d=t-w,u=e+w,p=t+w,i=f.data}}return i},bs.remove=function(e){if(isNaN(n=+this._x.call(null,e))||isNaN(o=+this._y.call(null,e)))return this;var t,s,i,r,n,o,a,l,h,c,d,u,p=this._root,_=this._x0,f=this._y0,g=this._x1,v=this._y1;if(!p)return this;if(p.length)for(;;){if((h=n>=(a=(_+g)/2))?_=a:g=a,(c=o>=(l=(f+v)/2))?f=l:v=l,t=p,!(p=p[d=c<<1|h]))return this;if(!p.length)break;(t[d+1&3]||t[d+2&3]||t[d+3&3])&&(s=t,u=d)}for(;p.data!==e;)if(i=p,!(p=p.next))return this;return(r=p.next)&&delete p.next,i?(r?i.next=r:delete i.next,this):t?(r?t[d]=r:delete t[d],(p=t[0]||t[1]||t[2]||t[3])&&p===(t[3]||t[2]||t[1]||t[0])&&!p.length&&(s?s[u]=p:this._root=p),this):(this._root=r,this)},bs.removeAll=function(e){for(var t=0,s=e.length;t<s;++t)this.remove(e[t]);return this},bs.root=function(){return this._root},bs.size=function(){var e=0;return this.visit(function(t){if(!t.length)do{++e}while(t=t.next)}),e},bs.visit=function(e){var t,s,i,r,n,o,a=[],l=this._root;for(l&&a.push(new _s(l,this._x0,this._y0,this._x1,this._y1));t=a.pop();)if(!e(l=t.node,i=t.x0,r=t.y0,n=t.x1,o=t.y1)&&l.length){var h=(i+n)/2,c=(r+o)/2;(s=l[3])&&a.push(new _s(s,h,c,n,o)),(s=l[2])&&a.push(new _s(s,i,c,h,o)),(s=l[1])&&a.push(new _s(s,h,r,n,c)),(s=l[0])&&a.push(new _s(s,i,r,h,c))}return this},bs.visitAfter=function(e){var t,s=[],i=[];for(this._root&&s.push(new _s(this._root,this._x0,this._y0,this._x1,this._y1));t=s.pop();){var r=t.node;if(r.length){var n,o=t.x0,a=t.y0,l=t.x1,h=t.y1,c=(o+l)/2,d=(a+h)/2;(n=r[0])&&s.push(new _s(n,o,a,c,d)),(n=r[1])&&s.push(new _s(n,c,a,l,d)),(n=r[2])&&s.push(new _s(n,o,d,c,h)),(n=r[3])&&s.push(new _s(n,c,d,l,h))}i.push(t)}for(;t=i.pop();)e(t.node,t.x0,t.y0,t.x1,t.y1);return this},bs.x=function(e){return arguments.length?(this._x=e,this):this._x},bs.y=function(e){return arguments.length?(this._y=e,this):this._y};var Ps={value:()=>{}};function As(){for(var e,t=0,s=arguments.length,i={};t<s;++t){if(!(e=arguments[t]+"")||e in i||/[\s.]/.test(e))throw new Error("illegal type: "+e);i[e]=[]}return new Ts(i)}function Ts(e){this._=e}function Ds(e,t){for(var s,i=0,r=e.length;i<r;++i)if((s=e[i]).name===t)return s.value}function Ls(e,t,s){for(var i=0,r=e.length;i<r;++i)if(e[i].name===t){e[i]=Ps,e=e.slice(0,i).concat(e.slice(i+1));break}return null!=s&&e.push({name:t,value:s}),e}Ts.prototype=As.prototype={constructor:Ts,on:function(e,t){var s,i,r=this._,n=(i=r,(e+"").trim().split(/^|\s+/).map(function(e){var t="",s=e.indexOf(".");if(s>=0&&(t=e.slice(s+1),e=e.slice(0,s)),e&&!i.hasOwnProperty(e))throw new Error("unknown type: "+e);return{type:e,name:t}})),o=-1,a=n.length;if(!(arguments.length<2)){if(null!=t&&"function"!=typeof t)throw new Error("invalid callback: "+t);for(;++o<a;)if(s=(e=n[o]).type)r[s]=Ls(r[s],e.name,t);else if(null==t)for(s in r)r[s]=Ls(r[s],e.name,null);return this}for(;++o<a;)if((s=(e=n[o]).type)&&(s=Ds(r[s],e.name)))return s},copy:function(){var e={},t=this._;for(var s in t)e[s]=t[s].slice();return new Ts(e)},call:function(e,t){if((s=arguments.length-2)>0)for(var s,i,r=new Array(s),n=0;n<s;++n)r[n]=arguments[n+2];if(!this._.hasOwnProperty(e))throw new Error("unknown type: "+e);for(n=0,s=(i=this._[e]).length;n<s;++n)i[n].value.apply(t,r)},apply:function(e,t,s){if(!this._.hasOwnProperty(e))throw new Error("unknown type: "+e);for(var i=this._[e],r=0,n=i.length;r<n;++r)i[r].value.apply(t,s)}};var Ms,Bs,Os=0,zs=0,Is=0,Ns=0,Fs=0,Hs=0,Ws="object"==typeof performance&&performance.now?performance:Date,Us="object"==typeof window&&window.requestAnimationFrame?window.requestAnimationFrame.bind(window):function(e){setTimeout(e,17)};function Ks(){return Fs||(Us(Vs),Fs=Ws.now()+Hs)}function Vs(){Fs=0}function js(){this._call=this._time=this._next=null}function qs(e,t,s){var i=new js;return i.restart(e,t,s),i}function Ys(){Fs=(Ns=Ws.now())+Hs,Os=zs=0;try{!function(){Ks(),++Os;for(var e,t=Ms;t;)(e=Fs-t._time)>=0&&t._call.call(void 0,e),t=t._next;--Os}()}finally{Os=0,function(){var e,t,s=Ms,i=1/0;for(;s;)s._call?(i>s._time&&(i=s._time),e=s,s=s._next):(t=s._next,s._next=null,s=e?e._next=t:Ms=t);Bs=e,Xs(i)}(),Fs=0}}function Gs(){var e=Ws.now(),t=e-Ns;t>1e3&&(Hs-=t,Ns=e)}function Xs(e){Os||(zs&&(zs=clearTimeout(zs)),e-Fs>24?(e<1/0&&(zs=setTimeout(Ys,e-Ws.now()-Hs)),Is&&(Is=clearInterval(Is))):(Is||(Ns=Ws.now(),Is=setInterval(Gs,1e3)),Os=1,Us(Ys)))}js.prototype=qs.prototype={constructor:js,restart:function(e,t,s){if("function"!=typeof e)throw new TypeError("callback is not a function");s=(null==s?Ks():+s)+(null==t?0:+t),this._next||Bs===this||(Bs?Bs._next=this:Ms=this,Bs=this),this._call=e,this._time=s,Xs()},stop:function(){this._call&&(this._call=null,this._time=1/0,Xs())}};const Js=4294967296;function Zs(e){return e.x}function Qs(e){return e.y}var ei=Math.PI*(3-Math.sqrt(5));function ti(e){var t,s=1,i=.001,r=1-Math.pow(i,1/300),n=0,o=.6,a=new Map,l=qs(d),h=As("tick","end"),c=function(){let e=1;return()=>(e=(1664525*e+1013904223)%Js)/Js}();function d(){u(),h.call("tick",t),s<i&&(l.stop(),h.call("end",t))}function u(i){var l,h,c=e.length;void 0===i&&(i=1);for(var d=0;d<i;++d)for(s+=(n-s)*r,a.forEach(function(e){e(s)}),l=0;l<c;++l)null==(h=e[l]).fx?h.x+=h.vx*=o:(h.x=h.fx,h.vx=0),null==h.fy?h.y+=h.vy*=o:(h.y=h.fy,h.vy=0);return t}function p(){for(var t,s=0,i=e.length;s<i;++s){if((t=e[s]).index=s,null!=t.fx&&(t.x=t.fx),null!=t.fy&&(t.y=t.fy),isNaN(t.x)||isNaN(t.y)){var r=10*Math.sqrt(.5+s),n=s*ei;t.x=r*Math.cos(n),t.y=r*Math.sin(n)}(isNaN(t.vx)||isNaN(t.vy))&&(t.vx=t.vy=0)}}function _(t){return t.initialize&&t.initialize(e,c),t}return null==e&&(e=[]),p(),t={tick:u,restart:function(){return l.restart(d),t},stop:function(){return l.stop(),t},nodes:function(s){return arguments.length?(e=s,p(),a.forEach(_),t):e},alpha:function(e){return arguments.length?(s=+e,t):s},alphaMin:function(e){return arguments.length?(i=+e,t):i},alphaDecay:function(e){return arguments.length?(r=+e,t):+r},alphaTarget:function(e){return arguments.length?(n=+e,t):n},velocityDecay:function(e){return arguments.length?(o=1-e,t):1-o},randomSource:function(e){return arguments.length?(c=e,a.forEach(_),t):c},force:function(e,s){return arguments.length>1?(null==s?a.delete(e):a.set(e,_(s)),t):a.get(e)},find:function(t,s,i){var r,n,o,a,l,h=0,c=e.length;for(null==i?i=1/0:i*=i,h=0;h<c;++h)(o=(r=t-(a=e[h]).x)*r+(n=s-a.y)*n)<i&&(l=a,i=o);return l},on:function(e,s){return arguments.length>1?(h.on(e,s),t):h.on(e)}}}function si(e){return new Map(e.map(e=>[e.id,e]))}function ii(e){const{entities:t,events:s,scopes:i,groups:r,width:n,height:o,sizeScale:a}=e,l=n/2,h=.84*o,c=Math.min(.4*n,.68*o),d=c,u=.84*c,p=Math.max(1,r.length),_=(d-u)/p,f=[],g=[],v=[],m=[],y={cx:l,cy:h,rInner:u,rOuter:d};if(!i.length||!t.length)return{nodes:f,dots:g,links:v,axis:m,band:y};const b=si(r),w=e=>(b.get(e.group)?.lane??0)%p,S=e=>b.get(e.group)?.color??"#8892a4",x=new Map(t.map(e=>[e.id,e])),$=i.length,k=i.reduce((e,t)=>e+Math.max(0,t.weight??1),0)||1,C=new Map;let E=0;for(const e of i){const t=Math.max(0,e.weight??1)/k;C.set(e.id,{from:E,width:t}),E+=t}const R=new Map;for(const e of s){const t=x.get(e.entityId);if(!t)continue;const s=C.get(e.scopeId);if(!s)continue;const i=s.from+Math.min(1,Math.max(0,e.t))*s.width,r=Math.PI-i*Math.PI,n=u+w(t)*_+_/2;g.push({x:l+n*Math.cos(r),y:h-n*Math.sin(r),entityId:t.id,scopeId:e.scopeId,color:S(t)});const o=R.get(t.id)??{sx:0,sy:0,count:0};o.sx+=Math.cos(r),o.sy+=Math.sin(r),o.count++,R.set(t.id,o)}const P=[],A=new Map,T=.62*c;for(const e of t){const t=R.get(e.id);if(!t||!t.count)continue;const s=Math.atan2(t.sy,t.sx),i=Math.hypot(t.sx,t.sy)/t.count,r=d+26+15*w(e)+(1-i)*T;P.push({entityId:e.id,r:(4+1.5*Math.sqrt(t.count))*a,tx:l+r*Math.cos(s),ty:h-r*Math.sin(s),x:l+r*Math.cos(s),y:h-r*Math.sin(s)}),A.set(e.id,e)}ti(P).force("x",function(e){var t,s,i,r=ws(.1);function n(e){for(var r,n=0,o=t.length;n<o;++n)(r=t[n]).vx+=(i[n]-r.x)*s[n]*e}function o(){if(t){var n,o=t.length;for(s=new Array(o),i=new Array(o),n=0;n<o;++n)s[n]=isNaN(i[n]=+e(t[n],n,t))?0:+r(t[n],n,t)}}return"function"!=typeof e&&(e=ws(null==e?0:+e)),n.initialize=function(e){t=e,o()},n.strength=function(e){return arguments.length?(r="function"==typeof e?e:ws(+e),o(),n):r},n.x=function(t){return arguments.length?(e="function"==typeof t?t:ws(+t),o(),n):e},n}(e=>e.tx).strength(.35)).force("y",function(e){var t,s,i,r=ws(.1);function n(e){for(var r,n=0,o=t.length;n<o;++n)(r=t[n]).vy+=(i[n]-r.y)*s[n]*e}function o(){if(t){var n,o=t.length;for(s=new Array(o),i=new Array(o),n=0;n<o;++n)s[n]=isNaN(i[n]=+e(t[n],n,t))?0:+r(t[n],n,t)}}return"function"!=typeof e&&(e=ws(null==e?0:+e)),n.initialize=function(e){t=e,o()},n.strength=function(e){return arguments.length?(r="function"==typeof e?e:ws(+e),o(),n):r},n.y=function(t){return arguments.length?(e="function"==typeof t?t:ws(+t),o(),n):e},n}(e=>e.ty).strength(.35)).force("collide",ks(e=>e.r+9).iterations(2)).stop().tick(120);const D=new Map;for(const e of P){const t=A.get(e.entityId),s={entityId:e.entityId,x:e.x??e.tx,y:e.y??e.ty,r:e.r,color:S(t),emphasis:t.emphasis};f.push(s),D.set(e.entityId,s)}for(const e of g){const t=D.get(e.entityId);if(!t)continue;const s=(t.x+e.x)/2,i=(t.y+e.y)/2;v.push({x1:t.x,y1:t.y,x2:e.x,y2:e.y,cx:s+.22*(l-s),cy:i+.22*(h-i),source:e.entityId,target:e.entityId,color:"#c8d2e0",typed:!1})}const L=(e,t,s)=>{const i=Math.PI-e*Math.PI,r=d+t;return{x:l+r*Math.cos(i),y:h-r*Math.sin(i),text:s}},M=e.axis??{start:"Start",middle:"Midpoint",end:"Finish"};if(m.push({x:l-d,y:h+20,text:M.start}),m.push({x:l+d,y:h+20,text:M.end}),m.push(L(.5,16,M.middle)),$>1&&$<=14)for(const e of i){const t=C.get(e.id);t.width<.02||m.push(L(t.from+t.width/2,-(d-u)-14,e.title))}return{nodes:f,dots:g,links:v,axis:m,band:y}}function ri(e){const{entities:t,relations:s,groups:i,relationKinds:r,width:n,height:o,sizeScale:a}=e,l=si(i),h=si(r),c=new Set(e.anchors??[]),d=new Map;for(const e of s)d.set(e.source,(d.get(e.source)??0)+1),d.set(e.target,(d.get(e.target)??0)+1);const u=t.map((e,s)=>{const i=d.get(e.id)??0,r=c.has(e.id),l=s/Math.max(1,t.length)*Math.PI*2,h=r?0:.3*Math.min(n,o);return{entityId:e.id,degree:i,anchor:r,r:(r?8:5)+Math.sqrt(i)*(r?4.2:3.2)*a,x:n/2+Math.cos(l)*h,y:o/2+Math.sin(l)*h}}),p=new Map(u.map(e=>[e.entityId,e])),_=s.filter(e=>p.has(e.source)&&p.has(e.target)).map(e=>({source:p.get(e.source),target:p.get(e.target),kind:e.kind})),f=ti(u).force("link",Rs(_).distance(90).strength(.35)).force("charge",function(){var e,t,s,i,r,n=ws(-30),o=1,a=1/0,l=.81;function h(s){var r,n=e.length,o=vs(e,Zs,Qs).visitAfter(d);for(i=s,r=0;r<n;++r)t=e[r],o.visit(u)}function c(){if(e){var t,s,i=e.length;for(r=new Array(i),t=0;t<i;++t)s=e[t],r[s.index]=+n(s,t,e)}}function d(e){var t,s,i,n,o,a=0,l=0;if(e.length){for(i=n=o=0;o<4;++o)(t=e[o])&&(s=Math.abs(t.value))&&(a+=t.value,l+=s,i+=s*t.x,n+=s*t.y);e.x=i/l,e.y=n/l}else{(t=e).x=t.data.x,t.y=t.data.y;do{a+=r[t.data.index]}while(t=t.next)}e.value=a}function u(e,n,h,c){if(!e.value)return!0;var d=e.x-t.x,u=e.y-t.y,p=c-n,_=d*d+u*u;if(p*p/l<_)return _<a&&(0===d&&(_+=(d=Ss(s))*d),0===u&&(_+=(u=Ss(s))*u),_<o&&(_=Math.sqrt(o*_)),t.vx+=d*e.value*i/_,t.vy+=u*e.value*i/_),!0;if(!(e.length||_>=a)){(e.data!==t||e.next)&&(0===d&&(_+=(d=Ss(s))*d),0===u&&(_+=(u=Ss(s))*u),_<o&&(_=Math.sqrt(o*_)));do{e.data!==t&&(p=r[e.data.index]*i/_,t.vx+=d*p,t.vy+=u*p)}while(e=e.next)}}return h.initialize=function(t,i){e=t,s=i,c()},h.strength=function(e){return arguments.length?(n="function"==typeof e?e:ws(+e),c(),h):n},h.distanceMin=function(e){return arguments.length?(o=e*e,h):Math.sqrt(o)},h.distanceMax=function(e){return arguments.length?(a=e*e,h):Math.sqrt(a)},h.theta=function(e){return arguments.length?(l=e*e,h):Math.sqrt(l)},h}().strength(-220)).force("center",function(e,t){var s,i=1;function r(){var r,n,o=s.length,a=0,l=0;for(r=0;r<o;++r)a+=(n=s[r]).x,l+=n.y;for(a=(a/o-e)*i,l=(l/o-t)*i,r=0;r<o;++r)(n=s[r]).x-=a,n.y-=l}return null==e&&(e=0),null==t&&(t=0),r.initialize=function(e){s=e},r.x=function(t){return arguments.length?(e=+t,r):e},r.y=function(e){return arguments.length?(t=+e,r):t},r.strength=function(e){return arguments.length?(i=+e,r):i},r}(n/2,o/2)).force("collide",ks(e=>e.r+12).iterations(2));c.size&&f.force("radial",function(e,t,s){var i,r,n,o=ws(.1);function a(e){for(var o=0,a=i.length;o<a;++o){var l=i[o],h=l.x-t||1e-6,c=l.y-s||1e-6,d=Math.sqrt(h*h+c*c),u=(n[o]-d)*r[o]*e/d;l.vx+=h*u,l.vy+=c*u}}function l(){if(i){var t,s=i.length;for(r=new Array(s),n=new Array(s),t=0;t<s;++t)n[t]=+e(i[t],t,i),r[t]=isNaN(n[t])?0:+o(i[t],t,i)}}return"function"!=typeof e&&(e=ws(+e)),null==t&&(t=0),null==s&&(s=0),a.initialize=function(e){i=e,l()},a.strength=function(e){return arguments.length?(o="function"==typeof e?e:ws(+e),l(),a):o},a.radius=function(t){return arguments.length?(e="function"==typeof t?t:ws(+t),l(),a):e},a.x=function(e){return arguments.length?(t=+e,a):t},a.y=function(e){return arguments.length?(s=+e,a):s},a}(e=>e.anchor?0:.34*Math.min(n,o),n/2,o/2).strength(e=>e.anchor?.35:.06)),f.stop().tick(360);const g=new Map(t.map(e=>[e.id,e])),v=u.map(e=>{const t=g.get(e.entityId);return{entityId:e.entityId,x:e.x??n/2,y:e.y??o/2,r:e.r,color:l.get(t.group)?.color??"#8892a4",emphasis:t.emphasis}}),m=_.map(e=>{const t=e.source,s=e.target;return{x1:t.x??0,y1:t.y??0,x2:s.x??0,y2:s.y??0,source:t.entityId,target:s.entityId,color:h.get(e.kind)?.color??"#7b8cff",typed:!0}});return{nodes:v,dots:[],links:m,axis:[]}}const ni="600 11px ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif";function oi(e,t,s){return[t*e.k+e.x,s*e.k+e.y]}function ai(e,t,s){return[(t-e.x)/e.k,(s-e.y)/e.k]}function li(e,t,s){if(!e.nodes.length)return{x:0,y:0,k:1};let i=1/0,r=1/0,n=-1/0,o=-1/0;const a=(e,t,s)=>{i=Math.min(i,e-s),r=Math.min(r,t-s),n=Math.max(n,e+s),o=Math.max(o,t+s)};for(const t of e.nodes)a(t.x,t.y,t.r+34);for(const t of e.dots)a(t.x,t.y,2);if(e.band){const{cx:t,cy:s,rOuter:i}=e.band;a(t-i,s-i,0),a(t+i,s+30,0)}const l=Math.min(1,.94*Math.min(t/(n-i),s/(o-r)));return{k:l,x:t/2-(i+n)/2*l,y:s/2-(r+o)/2*l}}function hi(e,t,s){const i=vs().x(e=>e.x).y(e=>e.y).addAll(e.nodes),r=i.find(t,s,40);return r&&Math.hypot(r.x-t,r.y-s)<=r.r+8?r.entityId:null}function ci(e,t,s,i,r,n){e.beginPath(),e.moveTo(t+n,s),e.arcTo(t+i,s,t+i,s+r,n),e.arcTo(t+i,s+r,t,s+r,n),e.arcTo(t,s+r,t,s,n),e.arcTo(t,s,t+i,s,n),e.closePath()}let di=class extends ae{constructor(){super(...arguments),this._dataset=null,this._error=null,this._loading=!0,this._view="web",this._options=hs,this._activeGroups=new Set,this._activeKinds=new Set,this._scopeIds=new Set,this._selected=null,this._hovered=null,this._sizeScale=1,this._showLabels=!0,this._layout={nodes:[],dots:[],links:[],axis:[]},this._camera={x:0,y:0,k:1},this._size={w:800,h:600},this._drag=null,this._onWheel=e=>{e.preventDefault();const t=this._canvas;if(!t)return;const s=t.getBoundingClientRect(),i=e.clientX-s.left,r=e.clientY-s.top,n=Math.min(12,Math.max(.05,this._camera.k*Math.pow(.999,e.deltaY)));this._camera={k:n,x:i-(i-this._camera.x)/this._camera.k*n,y:r-(r-this._camera.y)/this._camera.k*n},this._paint()},this._onPointerDown=e=>{e.currentTarget.setPointerCapture(e.pointerId),this._drag={x:e.clientX,y:e.clientY,cam:this._camera,moved:0}},this._onPointerMove=e=>{const t=e.currentTarget.getBoundingClientRect();if(this._drag){const t=e.clientX-this._drag.x,s=e.clientY-this._drag.y;return this._drag.moved=Math.max(this._drag.moved,Math.hypot(t,s)),this._camera={k:this._drag.cam.k,x:this._drag.cam.x+t,y:this._drag.cam.y+s},void this._paint()}const[s,i]=ai(this._camera,e.clientX-t.left,e.clientY-t.top),r=hi(this._layout,s,i);r!==this._hovered&&(this._hovered=r,this._paint())},this._onPointerUp=e=>{const t=this._drag;if(this._drag=null,!t||t.moved>4)return;const s=e.currentTarget.getBoundingClientRect(),[i,r]=ai(this._camera,e.clientX-s.left,e.clientY-s.top),n=hi(this._layout,i,r);this._selected=n&&n!==this._selected?n:null,this._paint()}}connectedCallback(){super.connectedCallback(),this._load()}disconnectedCallback(){super.disconnectedCallback(),this._observer?.disconnect()}async _load(){this._loading=!0,this._error=null;try{const e=await async function(e,t=hs){const[s,i,r,n]=await Promise.all([e.callWS({type:"config/entity_registry/list"}),e.callWS({type:"config/device_registry/list"}),e.callWS({type:"config/area_registry/list"}),e.callWS({type:"config_entries/get"}).catch(()=>[])]),o=s.filter(e=>t.includeHidden||!e.disabled_by&&!e.hidden_by),a=new Map(n.map(e=>[e.entry_id,e])),l=new Map(r.map(e=>[e.area_id,e])),h=new Map(i.map(e=>[e.id,e])),c=[],d=[],u=e=>c.push(e),p=(e,t,s,i,r)=>d.push({id:e,source:t,target:s,kind:i,label:r});for(const e of r)u({id:`area:${e.area_id}`,name:e.name,group:"area",kind:"Area",weight:0,meta:{"Area id":e.area_id,Floor:e.floor_id??"none"}});const _=new Map;for(const e of n){const t=_.get(e.domain)??[];t.push(e),_.set(e.domain,t)}for(const[e,t]of _)u({id:`integration:${e}`,name:e,group:"integration",kind:"Integration",weight:0,meta:{"Config entries":t.length,Titles:t.map(e=>e.title).slice(0,6).join(", ")}});const f=e=>e?a.get(e)?.domain??null:null;for(const e of i)if(t.includeHidden||!e.disabled_by){u({id:`device:${e.id}`,name:e.name_by_user??e.name??e.id,group:"device",kind:e.entry_type?`Device (${e.entry_type})`:"Device",weight:0,emphasis:!0,meta:{Manufacturer:e.manufacturer??"unknown",Model:e.model??"unknown",Area:e.area_id?l.get(e.area_id)?.name??e.area_id:"none","Device id":e.id}}),e.area_id&&l.has(e.area_id)&&p(`da:${e.id}`,`device:${e.id}`,`area:${e.area_id}`,"device_area","Area"),e.via_device_id&&h.has(e.via_device_id)&&p(`vd:${e.id}`,`device:${e.via_device_id}`,`device:${e.id}`,"via_device","Connected through");for(const t of e.config_entries){const s=f(t);s&&p(`id:${e.id}:${s}`,`integration:${s}`,`device:${e.id}`,"integration_device","Provides")}}const g=new Set(c.filter(e=>"device"===e.group).map(e=>e.id));for(const e of o){const t=`entity:${e.entity_id}`,s=e.entity_id.split(".")[0]??"unknown";if(u({id:t,name:e.name??e.original_name??e.entity_id,group:"entity",kind:s,weight:0,meta:{"Entity id":e.entity_id,Domain:s,Platform:e.platform,Category:e.entity_category??"primary",Device:e.device_id?h.get(e.device_id)?.name??e.device_id:"none"}}),e.device_id&&g.has(`device:${e.device_id}`))p(`de:${e.entity_id}`,`device:${e.device_id}`,t,"device_entity","Hosts");else{const s=f(e.config_entry_id)??e.platform;_.has(s)&&p(`ie:${e.entity_id}`,`integration:${s}`,t,"integration_entity","Provides")}e.area_id&&l.has(e.area_id)&&p(`ea:${e.entity_id}`,t,`area:${e.area_id}`,"entity_area","Area")}const v=new Map;for(const e of d)v.set(e.source,(v.get(e.source)??0)+1),v.set(e.target,(v.get(e.target)??0)+1);for(const e of c)e.weight=v.get(e.id)??0;const m=Date.now(),y=36e5*t.hours,b=Array.from({length:t.buckets},(e,s)=>({id:`w${s}`,title:new Date(m-y+s*y/t.buckets).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}),ordinal:s+1,subtitle:`${(t.hours/t.buckets).toFixed(1)}h`}));let w=[];try{w=await e.callWS({type:"logbook/get_events",start_time:us(m-y),end_time:us(m)})}catch{w=[]}const S=new Set(c.map(e=>e.id)),x=[];let $=0;for(const e of w){if(!e.entity_id)continue;const s=`entity:${e.entity_id}`;if(!S.has(s))continue;const i=(1e3*e.when-(m-y))/y;if(i<0||i>1)continue;const r=Math.min(t.buckets-1,Math.floor(i*t.buckets));x.push({id:"lb"+$++,scopeId:`w${r}`,entityId:s,t:i*t.buckets-r})}const k=c.filter(e=>"device"===e.group).length,C=c.filter(e=>"entity"===e.group).length;return{title:"Entity relationship map",subtitle:`${k} devices, ${C} entities, ${d.length} links, ${x.length} logbook events`,groups:cs,relationKinds:ds,scopes:b,entities:c,relations:d,events:x,axis:{start:`-${t.hours}h`,middle:`-${t.hours/2}h`,end:"now"},scopeNoun:["window","windows"],viewLabels:{arc:"Activity",web:"Relationships"},arcHint:`Activity over the last ${t.hours} hours from the logbook. Each dot is one event.`,webHint:"Registry relationships: devices host entities, live in areas and come from integrations."}}(this.hass,this._options);this._dataset=e,this._activeGroups=new Set(e.groups.map(e=>e.id)),this._activeKinds=new Set(e.relationKinds.map(e=>e.id));const t=[...e.scopes].sort((e,t)=>t.ordinal-e.ordinal)[0];this._scopeIds=new Set(e.scopes.map(e=>e.id)),!this._scopeIds.size&&t&&(this._scopeIds=new Set([t.id])),this._selected=null}catch(e){this._error=e instanceof Error?e.message:String(e)}finally{this._loading=!1,this.requestUpdate(),await this.updateComplete,this._attachCanvas(),this._rebuild(!0)}}get _canvas(){return this.renderRoot.querySelector("canvas")}_attachCanvas(){const e=this._canvas;e&&(this._observer?.disconnect(),this._observer=new ResizeObserver(()=>{const t=e.getBoundingClientRect();this._size={w:Math.max(1,t.width),h:Math.max(1,t.height)},this._rebuild(!0)}),this._observer.observe(e),e.addEventListener("wheel",this._onWheel,{passive:!1}))}_rebuild(e){const t=this._dataset;if(!t)return;const s=t.entities.filter(e=>this._activeGroups.has(e.group)),i=new Set(s.map(e=>e.id)),r=t.relations.filter(e=>this._activeKinds.has(e.kind)&&i.has(e.source)&&i.has(e.target));if("arc"===this._view){const e=t.scopes.filter(e=>this._scopeIds.has(e.id)).sort((e,t)=>e.ordinal-t.ordinal);this._layout=ii({entities:s,events:t.events,scopes:e,groups:t.groups,width:this._size.w,height:this._size.h,sizeScale:this._sizeScale,axis:t.axis})}else this._layout=ri({entities:s,relations:r,groups:t.groups,relationKinds:t.relationKinds,width:this._size.w,height:this._size.h,sizeScale:this._sizeScale,anchors:s.filter(e=>e.emphasis).map(e=>e.id)});e&&(this._camera=li(this._layout,this._size.w,this._size.h)),this._paint()}_paint(){const e=this._canvas,t=this._dataset;if(!e||!t)return;const s=Math.min(window.devicePixelRatio||1,2);e.width=Math.round(this._size.w*s),e.height=Math.round(this._size.h*s);const i=e.getContext("2d");if(!i)return;let r=null;if(this._selected&&(r=new Set([this._selected]),"web"===this._view))for(const e of t.relations)this._activeKinds.has(e.kind)&&(e.source===this._selected&&r.add(e.target),e.target===this._selected&&r.add(e.source));!function(e,t,s,i){const{layout:r,entities:n,camera:o,focus:a,hovered:l,selected:h}=i,c=i.dpr,d=()=>e.setTransform(c,0,0,c,0,0);d(),e.fillStyle="#05070a",e.fillRect(0,0,t,s),e.setTransform(o.k*c,0,0,o.k*c,o.x*c,o.y*c),e.lineCap="round";const u=e=>!a||a.has(e);if(r.band){const{cx:t,cy:s,rInner:i,rOuter:n}=r.band;e.beginPath(),e.arc(t,s,n,Math.PI,0),e.arc(t,s,i,0,Math.PI,!0),e.closePath(),e.fillStyle="rgba(190,198,210,0.10)",e.fill(),e.strokeStyle="rgba(190,198,210,0.16)",e.lineWidth=1/o.k,e.stroke()}const p=t=>{for(const s of r.links)(u(s.source)||u(s.target))===t&&(e.beginPath(),e.moveTo(s.x1,s.y1),void 0!==s.cx&&void 0!==s.cy?e.quadraticCurveTo(s.cx,s.cy,s.x2,s.y2):e.lineTo(s.x2,s.y2),e.strokeStyle=s.color,s.typed?(e.globalAlpha=t?.85:.1,e.lineWidth=(t?1.6:1)/o.k):(e.globalAlpha=t?.28:.05,e.lineWidth=(t?.9:.6)/o.k),e.stroke())};p(!1),p(!0),e.globalAlpha=1;for(const t of r.dots){const s=u(t.entityId);e.globalAlpha=s?.95:.16,e.fillStyle=s?t.color:"#8892a4",e.beginPath(),e.arc(t.x,t.y,(s?1.5:1.1)/o.k+.6,0,2*Math.PI),e.fill()}e.globalAlpha=1;for(const t of[...r.nodes].sort((e,t)=>e.r-t.r)){const s=u(t.entityId);e.globalAlpha=s?1:.2,e.beginPath(),e.arc(t.x,t.y,t.r,0,2*Math.PI),e.fillStyle=t.color,e.fill(),t.entityId===l||t.entityId===h?(e.strokeStyle="#ffffff",e.lineWidth=2/o.k):(e.strokeStyle="rgba(5,7,10,0.85)",e.lineWidth=1.2/o.k),e.stroke(),t.emphasis&&(e.beginPath(),e.arc(t.x,t.y,.42*t.r,0,2*Math.PI),e.fillStyle="rgba(5,7,10,0.65)",e.fill())}e.globalAlpha=1,d(),e.font="600 10px ui-sans-serif, system-ui, sans-serif",e.textBaseline="middle",e.textAlign="center",e.fillStyle="rgba(190,198,210,0.55)";for(const i of r.axis){const[r,n]=oi(o,i.x,i.y);r<-60||r>t+60||n<-20||n>s+20||e.fillText(i.text,r,n)}if(e.textAlign="left",!i.showLabels)return;const _=[...r.nodes].filter(e=>u(e.entityId)).sort((e,t)=>t.r-e.r).slice(0,55);for(const e of[l,h]){if(!e)continue;const t=r.nodes.find(t=>t.entityId===e);t&&!_.includes(t)&&_.push(t)}d(),e.font=ni,e.textBaseline="middle";const f=[],g=(e,t,s,i)=>f.some(([r,n,o,a])=>e<r+o&&e+s>r&&t<n+a&&t+i>n);for(const i of _){const r=n.get(i.entityId);if(!r)continue;const[a,c]=oi(o,i.x,i.y),d=e.measureText(r.name).width+14,u=18,p=a-d/2,_=c-i.r*o.k-u-6;if(p+d<0||p>t||_+u<0||_>s)continue;if(i.entityId!==l&&i.entityId!==h&&g(p-2,_-2,d+4,u+16))continue;f.push([p-2,_-2,d+4,u+16]),e.fillStyle="rgba(5,7,10,0.82)",e.strokeStyle=i.color,e.lineWidth=1,ci(e,p,_,d,u,5),e.fill(),e.stroke(),e.fillStyle="#e8eef6",e.fillText(r.name,p+7,_+u/2+.5);const v=String(r.weight);e.font="600 9px ui-sans-serif, system-ui, sans-serif";const m=e.measureText(v).width+8;e.fillStyle="rgba(5,7,10,0.9)",e.strokeStyle="rgba(190,198,210,0.45)",ci(e,a-i.r*o.k-m+2,_+u-2,m,13,6),e.fill(),e.stroke(),e.fillStyle="#b9c4d4",e.fillText(v,a-i.r*o.k-m+6,_+u+4.5),e.font=ni}}(i,this._size.w,this._size.h,{layout:this._layout,entities:new Map(t.entities.map(e=>[e.id,e])),camera:this._camera,showLabels:this._showLabels,hovered:this._hovered,selected:this._selected,focus:r,dpr:s})}_toggle(e,t,s){const i=new Set(e);i.has(t)?i.delete(t):i.add(t),s(i),this._rebuild(!0)}_exportPng(){const e=this._canvas;if(!e)return;const t=document.createElement("a");t.download=`ha-entity-map-${this._view}.png`,t.href=e.toDataURL("image/png"),t.click()}_renderLegend(e){const t={};for(const s of e.entities)t[s.group]=(t[s.group]??0)+1;const s={};for(const t of e.relations)s[t.kind]=(s[t.kind]??0)+1;return K`
      <div class="overlay legend">
        <h4>Shown &middot; click to filter</h4>
        ${e.groups.map(e=>K`
            <div
              class="row ${this._activeGroups.has(e.id)?"":"off"}"
              @click=${()=>this._toggle(this._activeGroups,e.id,e=>this._activeGroups=e)}
            >
              <span class="swatch" style="background:${e.color}"></span>
              <span>${e.label}</span>
              <span class="count">${t[e.id]??0}</span>
            </div>
          `)}
        ${"web"===this._view?K`
              <h4>Links &middot; click to filter</h4>
              ${e.relationKinds.map(e=>K`
                  <div
                    class="row ${this._activeKinds.has(e.id)?"":"off"}"
                    @click=${()=>this._toggle(this._activeKinds,e.id,e=>this._activeKinds=e)}
                  >
                    <span class="line" style="background:${e.color}"></span>
                    <span>${e.label}</span>
                    <span class="count">${s[e.id]??0}</span>
                  </div>
                `)}
            `:j}
      </div>
    `}_renderDetails(e){const t=e.entities.find(e=>e.id===this._selected);if(!t)return j;const s=e.relations.filter(e=>e.source===t.id||e.target===t.id),i=new Map(e.entities.map(e=>[e.id,e]));return K`
      <div class="overlay details">
        <h3>${t.name}</h3>
        <div style="color:#8b97a8">${t.kind??t.group}</div>
        <dl>
          ${Object.entries(t.meta??{}).map(([e,t])=>K`<dt>${e}</dt>
              <dd>${String(t)}</dd>`)}
          <dt>Links</dt>
          <dd>${s.length}</dd>
        </dl>
        ${s.slice(0,40).map(e=>{const s=i.get(e.source===t.id?e.target:e.source);return s?K`<div style="display:flex;gap:6px;align-items:center;padding:2px 0">
            <span style="color:#8b97a8">${e.label??e.kind}</span>
            <button
              style="margin-left:auto"
              @click=${()=>{this._selected=s.id,this._paint()}}
            >
              ${s.name}
            </button>
          </div>`:j})}
        <div style="margin-top:8px">
          <button @click=${()=>(this._selected=null,this._paint())}>Clear</button>
        </div>
      </div>
    `}render(){if(this._loading)return K`<div class="card"><p>Loading registries...</p></div>`;if(this._error)return K`<div class="card">
        <p>Could not build the map: ${this._error}</p>
        <button @click=${()=>this._load()}>Retry</button>
      </div>`;const e=this._dataset;return e?K`
      <div class="card">
        <div class="bar">
          <strong>${e.title}</strong>
          <span style="color:#8b97a8">${e.subtitle}</span>
          <span class="grow"></span>
          <label>
            Window
            <select
              @change=${e=>{const t=Number(e.target.value);this._options={...this._options,hours:t},this._load()}}
            >
              ${[6,12,24,48].map(e=>K`<option value=${e} ?selected=${e===this._options.hours}>${e}h</option>`)}
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              .checked=${this._options.includeHidden}
              @change=${e=>{const t=e.target.checked;this._options={...this._options,includeHidden:t},this._load()}}
            />
            Hidden and disabled
          </label>
          <label>
            Size
            <input
              type="range"
              min="0.4"
              max="2.2"
              step="0.05"
              .value=${String(this._sizeScale)}
              @input=${e=>{this._sizeScale=Number(e.target.value),this._rebuild(!1)}}
            />
          </label>
          <button
            @click=${()=>{this._showLabels=!this._showLabels,this._paint()}}
          >
            ${this._showLabels?"Hide labels":"Show labels"}
          </button>
          <button
            @click=${()=>{this._camera=li(this._layout,this._size.w,this._size.h),this._paint()}}
          >
            Fit
          </button>
          <button @click=${()=>this._exportPng()}>Export PNG</button>
          <button
            @click=${()=>{this._view="arc"===this._view?"web":"arc",this._rebuild(!0)}}
          >
            View: ${"arc"===this._view?e.viewLabels?.arc:e.viewLabels?.web}
          </button>
          <button @click=${()=>this._load()}>Refresh</button>
        </div>

        <div class="map">
          <canvas
            class=${this._drag?"dragging":""}
            @pointerdown=${this._onPointerDown}
            @pointermove=${this._onPointerMove}
            @pointerup=${this._onPointerUp}
            @pointerleave=${()=>(this._hovered=null,this._paint())}
          ></canvas>
          ${this._renderLegend(e)} ${this._renderDetails(e)}
          <div class="overlay hint">
            ${"arc"===this._view?e.arcHint:e.webHint} Drag to pan, wheel to
            zoom, click a node to focus.
          </div>
        </div>
      </div>
    `:j}};di.styles=[qe,a`
      .map {
        position: relative;
        height: calc(100vh - 220px);
        min-height: 420px;
        border: 1px solid var(--divider-color, #2a3442);
        border-radius: 8px;
        overflow: hidden;
        background: #05070a;
      }
      canvas {
        display: block;
        width: 100%;
        height: 100%;
        cursor: grab;
      }
      canvas.dragging {
        cursor: grabbing;
      }
      .bar {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }
      .bar .grow {
        flex: 1;
      }
      .overlay {
        position: absolute;
        background: rgba(19, 26, 36, 0.94);
        border: 1px solid #2a3442;
        border-radius: 8px;
        padding: 10px 12px;
        color: #e8eef6;
        font-size: 12px;
        max-height: calc(100% - 24px);
        overflow: auto;
      }
      .legend {
        top: 12px;
        left: 12px;
        min-width: 180px;
      }
      .details {
        top: 12px;
        right: 12px;
        width: 260px;
      }
      .legend h4 {
        margin: 0 0 6px;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #8b97a8;
      }
      .legend h4 + h4 {
        margin-top: 12px;
      }
      .legend .row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 3px 4px;
        border-radius: 4px;
        cursor: pointer;
      }
      .legend .row:hover {
        background: rgba(255, 255, 255, 0.05);
      }
      .legend .row.off {
        opacity: 0.38;
      }
      .legend .swatch {
        width: 10px;
        height: 10px;
        border-radius: 3px;
        flex: none;
      }
      .legend .line {
        width: 16px;
        height: 3px;
        border-radius: 2px;
        flex: none;
      }
      .legend .count {
        margin-left: auto;
        color: #8b97a8;
        font-variant-numeric: tabular-nums;
      }
      .details h3 {
        margin: 0 0 2px;
        font-size: 14px;
      }
      .details dl {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 3px 10px;
        margin: 8px 0 0;
      }
      .details dt {
        color: #8b97a8;
      }
      .details dd {
        margin: 0;
        text-align: right;
        word-break: break-word;
      }
      .hint {
        bottom: 12px;
        left: 12px;
        right: 12px;
        color: #8b97a8;
      }
    `],e([ue({attribute:!1})],di.prototype,"hass",void 0),e([pe()],di.prototype,"_dataset",void 0),e([pe()],di.prototype,"_error",void 0),e([pe()],di.prototype,"_loading",void 0),e([pe()],di.prototype,"_view",void 0),e([pe()],di.prototype,"_options",void 0),e([pe()],di.prototype,"_activeGroups",void 0),e([pe()],di.prototype,"_activeKinds",void 0),e([pe()],di.prototype,"_scopeIds",void 0),e([pe()],di.prototype,"_selected",void 0),e([pe()],di.prototype,"_hovered",void 0),e([pe()],di.prototype,"_sizeScale",void 0),e([pe()],di.prototype,"_showLabels",void 0),di=e([he("ha-soc-entity-map-view")],di);const ui={valid:!0,errors:[],warnings:[]},pi=e=>{const t=e;return{code:t?.code??"unknown_error",message:t?.message??String(e)}};let _i=class extends ae{constructor(){super(...arguments),this._listing=null,this._selected=null,this._loaded=null,this._draft="",this._verdict=ui,this._checking=!1,this._reason="",this._busy=!1,this._conflict=null,this._denial=null,this._saved=null,this._loading=!0}connectedCallback(){super.connectedCallback(),this._loadList()}disconnectedCallback(){super.disconnectedCallback(),this._validateTimer&&clearTimeout(this._validateTimer)}async _loadList(){this._loading=!0;try{this._listing=await(e=this.hass,we(e,{type:"ha_soc/dashboards/list"}))}catch(e){this._denial=pi(e)}finally{this._loading=!1}var e}async _select(e){this._conflict=null,this._saved=null,this._busy=!0;try{const t=await((e,t)=>we(e,{type:"ha_soc/dashboards/read",path:t}))(this.hass,e);this._selected=e,this._loaded=t,this._draft=t.content,this._reason="",this._verdict=ui,this._checking=!1}catch(e){this._denial=pi(e)}finally{this._busy=!1}}_onDraftChange(e){this._draft=e,this._saved=null,this._checking=!0,this._validateTimer&&clearTimeout(this._validateTimer),this._validateTimer=setTimeout(()=>{this._validate()},600)}async _validate(){const e=this._draft;try{const r=await(t=this.hass,s=e,i=this._selected??void 0,we(t,{type:"ha_soc/dashboards/validate",content:s,path:i}));if(e!==this._draft)return;this._verdict=r,this._checking=!1}catch(e){this._denial=pi(e),this._checking=!1}var t,s,i}_blockers(){const e=[];return this._loaded?this._draft===this._loaded.content&&e.push("No changes"):e.push("No file loaded"),this._checking&&e.push("Checking the YAML"),this._verdict.errors.length&&e.push("Fix the YAML error"),this._reason.trim()||e.push("Enter a reason"),this._busy&&e.push("Save in progress"),e}async _save(){if(this._loaded&&!this._blockers().length){this._busy=!0,this._conflict=null;try{const n=await(e=this.hass,t=this._loaded.path,s=this._draft,i=this._loaded.sha256,r=this._reason.trim(),we(e,{type:"ha_soc/dashboards/write",path:t,content:s,expected_sha256:i,reason:r}));this._loaded={path:n.path,content:this._draft,sha256:n.sha256},this._reason="",this._saved=`Saved. Previous copy kept at ${n.backup}`,await this._loadList()}catch(e){const t=pi(e);"conflict"===t.code?this._conflict={message:t.message}:this._denial=t}finally{this._busy=!1}var e,t,s,i,r}}async _reload(){this._selected&&await this._select(this._selected)}_syncGutter(e){const t=e.target,s=this.renderRoot.querySelector(".gutter");s&&(s.scrollTop=t.scrollTop)}render(){return this._denial?K`
        <div class="card banner denial">
          <h3>Request refused</h3>
          <p>${this._denial.message}</p>
          <p class="muted">Code: ${this._denial.code}</p>
          <button @click=${()=>{this._denial=null,this._loadList()}}>
            Dismiss
          </button>
        </div>
      `:this._loading?K`<div class="card"><p class="muted">Loading dashboard files...</p></div>`:this._listing?.enabled?this._listing.root_exists?K`
      <div class="layout">
        <div class="card">
          <h3>${this._listing.root}/</h3>
          ${this._listing.files.length?this._listing.files.map(e=>this._renderFile(e)):K`<p class="empty">No YAML files in this folder.</p>`}
          ${this._listing.truncated?K`<p class="muted">Listing truncated; only the first files are shown.</p>`:j}
        </div>

        <div class="card">${this._renderEditor()}</div>
      </div>
    `:K`
        <div class="card">
          <h3>Dashboard Files</h3>
          <p class="muted">
            No <code>${this._listing.root}</code> folder exists in the configuration
            directory. This view edits YAML-mode dashboards, which live in that folder;
            dashboards stored in the UI are edited in Home Assistant's own raw editor.
          </p>
        </div>
      `:K`
        <div class="card">
          <h3>Dashboard Files</h3>
          <p class="muted">
            Editing dashboard YAML files is turned off. The owner can turn it on under
            Settings, Dashboard Files. While it is off the server refuses every read and
            write, so nothing here is only hidden.
          </p>
        </div>
      `}_renderFile(e){return K`
      <button
        class="file"
        aria-current=${this._selected===e.path?"true":"false"}
        ?disabled=${e.too_large}
        @click=${()=>{this._select(e.path)}}
      >
        ${e.path}
        <span class="meta">
          ${s=e.size,s<1024?`${s} B`:`${Math.round(s/1024)} KB`} &middot; ${t=e.modified,new Date(1e3*t).toLocaleString()}
          ${e.too_large?K`&middot; too large to edit`:j}
        </span>
      </button>
    `;var t,s}_renderEditor(){if(!this._loaded)return K`<p class="empty">Select a file to edit.</p>`;const e=this._draft.split("\n").length,t=Array.from({length:e},(e,t)=>t+1).join("\n"),s=this._blockers();return K`
      <h3>${this._loaded.path}</h3>

      ${this._conflict?K`
            <div class="banner">
              <strong>${this._conflict.message}</strong>
              <p class="muted">
                Your draft is still here. Copy anything you need, then reload to get the
                file as it now stands on disk.
              </p>
              <button @click=${()=>{this._reload()}}>Reload from disk</button>
            </div>
          `:j}

      ${this._saved?K`<p class="muted">${this._saved}</p>`:j}

      <div class="editor">
        <div class="gutter">${t}</div>
        <textarea
          spellcheck="false"
          .value=${this._draft}
          ?readonly=${this._busy}
          @scroll=${this._syncGutter}
          @input=${e=>this._onDraftChange(e.target.value)}
        ></textarea>
      </div>

      ${this._renderDiagnostics()}

      <div class="commit">
        <input
          type="text"
          placeholder="Why are you changing this file?"
          .value=${this._reason}
          maxlength="500"
          @input=${e=>this._reason=e.target.value}
        />
        <button ?disabled=${s.length>0} @click=${()=>{this._save()}}>
          Save
        </button>
        ${s.length?K`<span class="muted">${s[0]}</span>`:j}
      </div>
    `}_renderDiagnostics(){return this._checking?K`<p class="muted">Checking the YAML on the server...</p>`:this._verdict.errors.length||this._verdict.warnings.length?K`
      ${this._verdict.errors.map(e=>K`
          <p class="diag error">
            Error${e.line?K` (line ${e.line})`:j}: ${e.message}
          </p>
        `)}
      ${this._verdict.warnings.map(e=>K`
          <p class="diag warning">
            Warning${e.line?K` (line ${e.line})`:j}: ${e.message}
          </p>
        `)}
    `:K`<p class="muted">No YAML errors or warnings.</p>`}};var fi;_i.styles=[qe,a`
      .layout {
        display: grid;
        grid-template-columns: minmax(200px, 260px) 1fr;
        gap: 16px;
        align-items: start;
      }
      @container (max-width: 800px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
      .file {
        display: block;
        width: 100%;
        text-align: left;
        padding: 6px 8px;
        border: none;
        background: none;
        border-radius: 6px;
        cursor: pointer;
        font: inherit;
        color: inherit;
      }
      .file[aria-current="true"] {
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
      }
      .file .meta {
        display: block;
        font-size: 11px;
        opacity: 0.75;
      }
      .editor {
        display: flex;
        border: 1px solid var(--divider-color, #444);
        border-radius: 6px;
        overflow: hidden;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
        font-size: 12.5px;
        line-height: 1.5;
      }
      .gutter {
        padding: 8px 6px;
        text-align: right;
        user-select: none;
        opacity: 0.55;
        overflow: hidden;
        background: rgba(127, 127, 127, 0.08);
        white-space: pre;
      }
      textarea {
        flex: 1;
        min-height: 420px;
        border: none;
        outline: none;
        resize: vertical;
        padding: 8px;
        font: inherit;
        color: inherit;
        background: transparent;
        white-space: pre;
        overflow-wrap: normal;
        overflow-x: auto;
      }
      .diag {
        margin: 4px 0;
        padding-left: 8px;
        border-left: 3px solid transparent;
      }
      .diag.error {
        border-left-color: var(--error-color, #db4437);
      }
      .diag.warning {
        border-left-color: var(--warning-color, #ffa600);
      }
      .banner {
        border-left: 4px solid var(--warning-color, #ffa600);
        padding: 8px 12px;
        margin-bottom: 12px;
      }
      .banner.denial {
        border-left-color: var(--error-color, #db4437);
      }
      .commit {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-top: 12px;
      }
      .commit input[type="text"] {
        flex: 1;
        min-width: 200px;
        padding: 6px 8px;
      }
    `],e([ue({attribute:!1})],_i.prototype,"hass",void 0),e([pe()],_i.prototype,"_listing",void 0),e([pe()],_i.prototype,"_selected",void 0),e([pe()],_i.prototype,"_loaded",void 0),e([pe()],_i.prototype,"_draft",void 0),e([pe()],_i.prototype,"_verdict",void 0),e([pe()],_i.prototype,"_checking",void 0),e([pe()],_i.prototype,"_reason",void 0),e([pe()],_i.prototype,"_busy",void 0),e([pe()],_i.prototype,"_conflict",void 0),e([pe()],_i.prototype,"_denial",void 0),e([pe()],_i.prototype,"_saved",void 0),e([pe()],_i.prototype,"_loading",void 0),_i=e([he("ha-soc-dashboard-files-view")],_i);const gi={core:"Core",hacs:"HACS",custom:"Custom"},vi={core:"good",hacs:"medium",custom:"high"},mi={core:0,hacs:1,custom:2},yi={custom_repo:"Custom repo",custom_source_list:"Custom source-list"};let bi=fi=class extends Je{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._error=null,this._refreshing=!1,this._search="",this._tierFilter="all",this._limit=25,this._intSort=null,this._containerSort=null,this._containers=null,this._containersLoading=!0,this._watchdog=null,this._editSlug=null,this._wdError=null,this._hacs=null,this._hacsBusy=null,this._hacsError=null,this._hacsRefresh=null,this._hacsUpdate=null,this._hacsSort=null,this._hacsCategoryFilter="all",this._hacsOwnerFilter=[],this._hacsOwnersSeeded=!1,this._hacsUnsub=null,this._isOwner=!1,this._crash=null,this._crashLoading=!0,this._crashError=null,this._crashExpanded=null,this._crashFiles={},this._crashFileError=null,this._crashCollecting=!1,this._crashCollectResult=null,this._crashFeedback=null}get viewId(){return"integration_security"}connectedCallback(){var e,t,s;super.connectedCallback(),this._load(),this._loadContainers(),this._loadWatchdog(),this._loadHacs(),this._loadCrash(),Me(this.hass).then(e=>{this._isOwner=!!e.is_owner}).catch(()=>{this._isOwner=!1}),(e=this.hass,t="hacs",s=()=>{this._loadHacs()},e.connection.subscribeMessage(()=>s(),{type:"ha_soc/subscribe",topic:t})).then(e=>{this._hacsUnsub=e})}disconnectedCallback(){super.disconnectedCallback(),this._hacsUnsub?.(),this._hacsUnsub=null}async _loadHacs(){try{this._hacs=await(e=this.hass,we(e,{type:"ha_soc/hacs/status"})),this._hacsOwnersSeeded||(this._hacsOwnerFilter=[...this._hacs.owner_filter],this._hacsOwnersSeeded=!0)}catch(e){this._hacs=null,this._hacsError=e?.message??String(e)}var e}async _toggleHacsOwner(e){const t=this._hacsOwnerFilter.includes(e)?this._hacsOwnerFilter.filter(t=>t!==e):[...this._hacsOwnerFilter,e];this._hacsOwnerFilter=t;try{this._hacs=await(s=this.hass,i=t,we(s,{type:"ha_soc/hacs/set_owners",owners:i}))}catch(e){this._hacsError=e?.message??String(e)}var s,i}async _hacsRefreshAll(){const e=this._hacsOwnerFilter.length?this._hacsOwnerFilter:void 0;this._hacsBusy="refresh",this._hacsError=null,this._hacsRefresh=null;try{this._hacsRefresh=await(t=this.hass,s={owners:e},we(t,{type:"ha_soc/hacs/refresh_all",...s?.owners?{owners:s.owners}:{},...s?.repositoryIds?{repository_ids:s.repositoryIds}:{}})),await this._loadHacs()}catch(e){this._hacsError=e?.message??String(e)}finally{this._hacsBusy=null}var t,s}async _hacsUpdateAll(){const e=this._hacsOwnerFilter.length?this._hacsOwnerFilter:void 0,t=this._filteredHacs().filter(e=>e.pending_update);if(!t.length)return;const s=t.map(e=>`${e.full_name} (${e.installed_version??"?"} → ${e.available_version??"?"})`);if(window.confirm(`Install ${t.length} HACS update(s) now?\n\n${s.join("\n")}\n\nIntegrations take effect after a Home Assistant restart. This is audited.`)){this._hacsBusy="update",this._hacsError=null,this._hacsUpdate=null;try{this._hacsUpdate=await(i=this.hass,r={owners:e},we(i,{type:"ha_soc/hacs/update_all",...r?.owners?{owners:r.owners}:{},...r?.repositoryIds?{repository_ids:r.repositoryIds}:{}})),await this._loadHacs(),await this._load()}catch(e){this._hacsError=e?.message??String(e)}finally{this._hacsBusy=null}var i,r}}async _loadWatchdog(){try{this._watchdog=await(e=this.hass,we(e,{type:"ha_soc/watchdog/status"}))}catch{this._watchdog=null}var e}async _loadCrash(){this._crashLoading=!0;try{this._crash=await(e=this.hass,we(e,{type:"ha_soc/crash_forensics/status"})),this._crashError=null}catch(e){this._crash=null,this._crashError=e?.message??String(e)}finally{this._crashLoading=!1}var e}_toggleCrashRow(e){this._crashExpanded=this._crashExpanded===e?null:e}async _viewCrashFile(e,t){const s=`${e}/${t}`;this._crashFileError=null;try{const i=await ye(this.hass,e,t);this._crashFiles={...this._crashFiles,[s]:i}}catch(e){this._crashFileError=e?.message??String(e)}}async _exportCrashFile(e,t,s){const i=`${e}/${t}`;let r=this._crashFiles[i];this._crashFileError=null;try{void 0===r&&(r=await ye(this.hass,e,t),this._crashFiles={...this._crashFiles,[i]:r});const n=qt(r),o=jt(r);"copy"===s?await Yt(r):Gt(r,`${e}-${t}-${Xt()}.txt`);const a=await Vt(r);await je(this.hass,"copy"===s?"copy_forensics":"download_forensics",n,o,a),this._crashFeedback=`${"copy"===s?"Copied":"Downloaded"} ${t} (${n} line(s))`}catch(e){this._crashFileError=e?.message??String(e)}}async _crashCollectNow(){if(window.confirm("Run a crash-forensics collection now, as a dry run against the CURRENT boot?\n\nThis calls the same Supervisor endpoints a real unclean-stop collection uses, writes a bundle, and is audited. It does not affect a real crash detection.")){this._crashCollecting=!0,this._crashError=null,this._crashCollectResult=null;try{const t=await(e=this.hass,we(e,{type:"ha_soc/crash_forensics/collect_now"})),s=t?.bundle;this._crashCollectResult=s?{id:s.bundle_id,ts:s.heartbeat?.ts??null,classification:s.classification??null,gap_seconds:s.gap_seconds??null,suspects:s.suspects??[],size_bytes:0,path:""}:null,await this._loadCrash()}catch(e){this._crashError=e?.message??String(e)}finally{this._crashCollecting=!1}var e}}async _setWatchdog(e){this._wdError=null;try{this._watchdog=await((e,t)=>we(e,{type:"ha_soc/watchdog/set",...t}))(this.hass,e)}catch(e){this._wdError=e&&"object"==typeof e&&"code"in e&&"unauthorized"===e.code?"Watchdog and cap configuration are available to the account owner only.":`Could not save: ${e instanceof Error?e.message:JSON.stringify(e)}`}}async _load(){this._loading=!0,this._error=null;try{this._overview=await(e=this.hass,we(e,{type:"ha_soc/integration_security/list"}))}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}var e}async _loadContainers(){this._containersLoading=!0;try{this._containers=await(e=this.hass,we(e,{type:"ha_soc/containers/resources"}))}catch{this._containers=null}finally{this._containersLoading=!1}var e}async _onRefresh(){this._refreshing=!0;try{await(e=this.hass,we(e,{type:"ha_soc/integration_security/refresh"})),await this._load()}finally{this._refreshing=!1}var e}_filtered(){const e=this._overview?.integrations??[],t=this._search.trim().toLowerCase(),s=e.filter(e=>"all"===this._tierFilter||e.tier===this._tierFilter).filter(e=>!t||e.name.toLowerCase().includes(t)||e.domain.toLowerCase().includes(t));return this._intSort?Ze(s,this._intSort,fi.INTEGRATION_SORT):s.sort((e,t)=>e.name.localeCompare(t.name))}render(){if(this._loading)return K`<div class="empty">Loading integrations…</div>`;if(this._error||!this._overview)return K`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Integration Security</h3>
          <p style="font-size:13px;">${this._error??"The server returned no data."}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const e=this._overview,t=this._filtered(),s=t.slice(0,this._limit),i=this._intSort,r=e=>{this._intSort=e,this._limit=25},n=[{id:"integration_security",title:"Integration Security",hideable:!1,render:()=>K`
      <div class="card">
        <h3>Integration Security</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">provenance, not safety</span> This measures how much is
          known about where each integration's code came from and how it's maintained — it
          is <strong>not</strong> a verdict that the code is safe to run. Home Assistant
          runs integrations in-process with no sandbox; a high-provenance integration can
          still do anything a low-provenance one can.
        </p>

        <div class="toolbar" style="margin-top:12px;">
          <div class="pill" style="--tone-unused:0">
            <span class="dot" style="background:var(--success-color,#43a047);"></span>
            Core ${e.tier_counts.core}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--warning-color,#ffa600);"></span>
            HACS ${e.tier_counts.hacs}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--error-color,#db4437);"></span>
            Custom ${e.tier_counts.custom}
          </div>
          <span class="spacer"></span>
          <button class="ha-btn" ?disabled=${this._refreshing||!e.github_configured} @click=${this._onRefresh}>
            ${this._refreshing?"Refreshing…":"Refresh GitHub signals"}
          </button>
        </div>

        ${e.github_configured?e.refreshed_at?K`<p class="muted" style="font-size:12px;margin:0 0 4px;">
                GitHub signals last refreshed ${new Date(e.refreshed_at).toLocaleString()}.
              </p>`:j:K`<p class="muted" style="font-size:12px;margin:0 0 4px;">
              GitHub-derived signals are <strong>not collected</strong> — set a GitHub token
              in the owner-only Settings tab to enable them.
            </p>`}
        ${e.hacs_installed&&!e.hacs_source_introspectable?K`<p class="muted" style="font-size:12px;margin:0;">
              HACS is installed but its per-repository source (default store vs. custom
              repo) isn't readable here, so HACS-managed content is shown as
              <em>Custom</em> and source flags are unverified.
            </p>`:j}
      </div>

      <div class="card">
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search integrations…"
            .value=${this._search}
            @input=${e=>{this._search=e.target.value,this._limit=25}}
            style="flex:1 1 220px;"
          />
          <select
            .value=${this._tierFilter}
            @change=${e=>{this._tierFilter=e.target.value,this._limit=25}}
          >
            <option value="all">All tiers</option>
            <option value="core">Core</option>
            <option value="hacs">HACS</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        ${t.length?K`
              <div style="overflow-x:auto;">
                <table>
                  <thead>
                    <tr>
                      ${Qe("Integration","name",i,r)}
                      ${Qe("Source","tier",i,r)}
                      ${Qe("Quality","quality",i,r)}
                      ${Qe("License","license",i,r)}
                      ${Qe("Scanner","scanner",i,r)}
                      ${Qe("Signed","signed",i,r)}
                      ${Qe("Release","release",i,r)}
                      ${Qe("Stars","stars",i,r)}
                      ${Qe("Last push","pushed",i,r)}
                    </tr>
                  </thead>
                  <tbody>
                    ${s.map(e=>this._renderRow(e))}
                  </tbody>
                </table>
              </div>
              ${t.length>this._limit?K`
                    <div class="toolbar" style="justify-content:center;margin-top:12px;">
                      <button class="ha-btn" @click=${()=>this._limit+=25}>
                        Show more (${t.length-this._limit} more)
                      </button>
                    </div>
                  `:j}
              <p class="muted" style="font-size:11.5px;margin-top:8px;">
                Showing ${Math.min(this._limit,t.length)} of ${t.length}.
              </p>
            `:K`<div class="empty">No integrations match.</div>`}
      </div>
        `},{id:"hacs_updates",title:"HACS Updates",render:()=>this._renderHacs()},{id:"container_resources",title:"Container Resource Usage",render:()=>this._renderContainers()},{id:"crash_forensics",title:"Crash Forensics",render:()=>this._renderCrashForensics()}];return this._renderSections(n)}_notCollected(){return K`<span class="muted" title="No GitHub token, or no repo URL discovered">—</span>`}_fmtBytes(e){if(null==e)return"—";if(e<1024)return`${e} B`;const t=["KB","MB","GB","TB"];let s=e/1024,i=0;for(;s>=1024&&i<t.length-1;)s/=1024,i++;return`${s.toFixed(s>=100?0:1)} ${t[i]}`}_pctCell(e,t){if(null==e)return K`<span class="muted">—</span>`;return K`<span style="font-weight:600;color:${t?"var(--status-critical)":e>=60?"var(--status-warning)":"inherit"};font-variant-numeric:tabular-nums;"
      >${e.toFixed(1)}%</span
    >`}_filteredHacs(){const e=this._hacs?.repositories??[],t=this._hacsOwnerFilter,s=e.filter(e=>"all"===this._hacsCategoryFilter||e.category===this._hacsCategoryFilter).filter(e=>!t.length||t.includes(e.owner.toLowerCase()));return this._hacsSort?Ze(s,this._hacsSort,fi.HACS_SORT):s}_renderHacs(){const e=this._hacs,t=this._filteredHacs(),s=t.filter(e=>e.pending_update),i=this._hacsOwnerFilter.length>0,r=null!==this._hacsBusy||Boolean(e?.refresh_in_progress),n=e=>e?new Date(e).toLocaleString():"never",o=e?Array.from(new Set(e.repositories.map(e=>e.category))).sort():[],a=e?.owners??[],l=this._hacsSort,h=e=>{this._hacsSort=e};return K`
      <div class="card">
        <h3>HACS Updates</h3>
        <p class="muted" style="margin-top:-4px;font-size:12.5px;">
          HACS re-checks each repository on its own schedule. Refresh forces that check, bounded
          to a few repositories at a time instead of one at a time; Install runs the same update
          as clicking each update entity. Both are owner-only and audited, and can be narrowed to
          one or more GitHub owners below.
        </p>
        ${this._hacsError?K`<div class="alert">${this._hacsError}</div>`:j}
        ${e?e.available?K`
                ${a.length?K`
                      <div class="toolbar" style="flex-wrap:wrap;gap:6px;margin-bottom:8px;">
                        ${a.map(e=>{const t=this._hacsOwnerFilter.includes(e.owner);return K`
                            <button
                              class="ha-btn ${t?"ha-btn-active":""}"
                              style="font-size:12px;padding:2px 10px;"
                              ?disabled=${r}
                              @click=${()=>this._toggleHacsOwner(e.owner)}
                            >
                              ${e.owner} (${e.count}, ${e.pending} pending)
                            </button>
                          `})}
                      </div>
                    `:j}
                <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px;">
                  <button class="ha-btn" ?disabled=${r} @click=${()=>this._hacsRefreshAll()}>
                    ${(()=>{if(e?.refresh_in_progress){const t=e.refresh_failed?`, ${e.refresh_failed} failed`:"";return`Refreshing ${e.refresh_done} / ${e.refresh_total}${t}`}return"refresh"===this._hacsBusy?"Refreshing…":i?`Refresh selected (${t.length})`:`Refresh all (${e?.repositories.length??0})`})()}
                  </button>
                  <button class="ha-btn" ?disabled=${r||!s.length} @click=${()=>this._hacsUpdateAll()}>
                    ${"update"===this._hacsBusy?"Installing…":`Install ${s.length} pending`}
                  </button>
                  <span class="muted" style="font-size:12px;">
                    Last refresh ${n(e.last_refresh)} · last install ${n(e.last_update)}
                  </span>
                </div>
                ${this._hacsRefresh?K`<p class="muted" style="font-size:12px;">
                      Refreshed ${this._hacsRefresh.refreshed.length}${this._hacsRefresh.failed.length?`, ${this._hacsRefresh.failed.length} failed`:""};
                      ${this._hacsRefresh.pending_after.length} update(s) pending.
                    </p>`:j}
                ${this._hacsUpdate?K`<p class="muted" style="font-size:12px;">
                      Installed ${this._hacsUpdate.installed.length}${this._hacsUpdate.failed.length?`, ${this._hacsUpdate.failed.length} failed`:""}${this._hacsUpdate.skipped.length?`, ${this._hacsUpdate.skipped.length} skipped`:""}.
                      ${this._hacsUpdate.restart_needed?K`<strong>Restart Home Assistant to load the new integration code.</strong>`:j}
                    </p>`:j}
                ${this._hacsUpdate?.failed.length?K`<ul class="muted" style="font-size:12px;">${this._hacsUpdate.failed.map(e=>K`<li>${e.full_name}: ${e.error}</li>`)}</ul>`:j}
                <div class="toolbar">
                  <select
                    .value=${this._hacsCategoryFilter}
                    @change=${e=>{this._hacsCategoryFilter=e.target.value}}
                  >
                    <option value="all">All categories</option>
                    ${o.map(e=>K`<option value=${e}>${e}</option>`)}
                  </select>
                </div>
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${Qe("Repository","name",l,h)}
                        ${Qe("Category","category",l,h)}
                        ${Qe("Installed","installed",l,h)}
                        ${Qe("Available","available",l,h)}
                        ${Qe("Author","author",l,h)}
                        ${Qe("Released","updated",l,h)}
                        <th>State</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${t.map(e=>K`
                          <tr>
                            <td class="mono">${e.full_name}</td>
                            <td>${e.category}</td>
                            <td class="mono">${e.installed_version??"—"}</td>
                            <td class="mono">${e.available_version??"—"}</td>
                            <td>${e.authors.length?e.authors.join(", "):"—"}</td>
                            <td class="muted" style="font-size:11.5px;" title=${e.last_updated??""}>
                              ${(e=>{if(!e)return"—";const t=new Date(e).getTime();if(Number.isNaN(t))return"—";const s=Math.floor((Date.now()-t)/864e5);return s<0?"—":0===s?"today":`${s} day${1===s?"":"s"} ago`})(e.last_updated)}
                            </td>
                            <td>
                              ${e.in_progress?K`<span class="pill medium"><span class="dot"></span>installing</span>`:e.pending_update?K`<span class="pill medium"><span class="dot"></span>update pending</span>`:K`<span class="pill good"><span class="dot"></span>current</span>`}
                            </td>
                          </tr>
                        `)}
                    </tbody>
                  </table>
                </div>
              `:K`<p class="muted">${e.reason??"HACS is not available."}</p>`:K`<p class="muted">Loading HACS state…</p>`}
      </div>
    `}_renderContainers(){const e=this._containers,t=this._containerSort,s=e=>this._containerSort=e;return K`
      <div class="card">
        <div class="toolbar">
          <h3 style="margin:0;flex:1;">Container Resource Usage</h3>
          <button class="ha-btn" ?disabled=${this._containersLoading} @click=${()=>this._loadContainers()}>
            ${this._containersLoading?"Refreshing…":"Refresh"}
          </button>
        </div>
        <p class="muted" style="margin-top:-4px;font-size:12.5px;">
          Live per-container CPU and memory for every add-on plus Home Assistant Core and
          the Supervisor. A container sitting near its <strong>memory limit</strong> (or
          pinning CPU) is the usual signal for the one that's OOM-killing / restart-looping
          and dragging the host down — those float to the top and are flagged.
        </p>
        ${this._renderWatchdogBar()}
        ${this._containersLoading&&!e?K`<div class="empty">Loading container stats…</div>`:e&&e.available?e.containers.length?K`
                  <div style="overflow-x:auto;">
                    <table>
                      <thead>
                        <tr>
                          ${Qe("Container","name",t,s)}
                          ${Qe("State","state",t,s)}
                          ${Qe("CPU","cpu",t,s,{numeric:!0})}
                          ${Qe("Memory","memory",t,s,{numeric:!0})}
                          ${Qe("Used / Limit","usage",t,s)}
                          ${Qe("Net ↓/↑","net",t,s)}
                          ${Qe("Disk R/W","disk",t,s)}
                          ${Qe("Flags","flags",t,s)}
                          <th>Watchdog / Cap</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${Ze(e.containers,t,fi.CONTAINER_SORT).map(e=>this._renderContainerRow(e))}
                      </tbody>
                    </table>
                  </div>
                  ${this._renderEditor()}
                  ${this._renderWatchdogActivity()}
                  <p class="muted" style="font-size:11.5px;margin-top:8px;">
                    Updated ${new Date(e.generated_at).toLocaleTimeString()}. CPU/memory are
                    an instantaneous sample — click Refresh to re-poll.
                  </p>
                `:K`<div class="empty">No containers reported.</div>`:K`<div class="empty">
                ${"not_supervisor"===e?.reason?"Per-container stats need a Supervisor-based install (Home Assistant OS or Supervised). This install doesn't run under Supervisor, so there are no add-on containers to measure.":"Container stats aren't available right now."}
              </div>`}
      </div>
    `}_renderWatchdogBar(){const e=this._watchdog;if(!e)return j;const t=e.config;return K`
      <div
        style="border:1px solid var(--divider-color);border-radius:10px;padding:10px 14px;margin-bottom:12px;"
      >
        <div class="toolbar" style="margin-bottom:${t.enabled?"8px":"0"};">
          <label style="display:inline-flex;align-items:center;gap:8px;font-weight:600;font-size:13.5px;cursor:pointer;">
            <input
              type="checkbox"
              .checked=${t.enabled}
              @change=${e=>this._setWatchdog({enabled:e.target.checked})}
            />
            Resource Watchdog
          </label>
          <span class="muted" style="font-size:12px;">
            ${t.enabled?`sampling every ${t.interval_seconds}s — acts after ${t.sustained_samples} sustained breaches`:"off — no automatic detection or action (owner-only setting)"}
          </span>
        </div>
        ${t.enabled?K`
              <div class="toolbar" style="gap:14px;margin-bottom:0;">
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  CPU ≥
                  <input type="number" min="10" max="100" style="width:64px;" .value=${String(t.default_cpu_percent)}
                    @change=${e=>this._setWatchdog({default_cpu_percent:Number(e.target.value)})} />%
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Memory ≥
                  <input type="number" min="10" max="100" style="width:64px;" .value=${String(t.default_memory_percent)}
                    @change=${e=>this._setWatchdog({default_memory_percent:Number(e.target.value)})} />%
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Default action
                  <select .value=${t.default_action}
                    @change=${e=>this._setWatchdog({default_action:e.target.value})}>
                    <option value="alert" ?selected=${"alert"===t.default_action}>Alert only</option>
                    <option value="restart" ?selected=${"restart"===t.default_action}>Restart add-on</option>
                    <option value="stop" ?selected=${"stop"===t.default_action}>Stop add-on</option>
                  </select>
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Sustained samples
                  <input type="number" min="1" max="30" style="width:56px;" .value=${String(t.sustained_samples)}
                    @change=${e=>this._setWatchdog({sustained_samples:Number(e.target.value)})} />
                </label>
              </div>
              <p class="muted" style="font-size:11.5px;margin:6px 0 0;">
                Home Assistant Core and the Supervisor are always alert-only — the watchdog
                never auto-restarts them, whatever the default. After 3 enforcement actions
                on one container within an hour it downgrades that container to alert-only
                (a restart loop needs a human, not more restarts).
              </p>
            `:j}
        ${this._wdError?K`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin:6px 0 0;">${this._wdError}</p>`:j}
      </div>
    `}_wdCell(e){const t=this._watchdog;if(!t)return K`<span class="muted">—</span>`;const s=t.config,i=s.overrides?.[e.slug]??{},r=i.cpu_percent??s.default_cpu_percent,n=i.memory_percent??s.default_memory_percent,o="addon"===e.kind?i.action??s.default_action:"alert",a=s.hard_limits?.[e.slug],l=t.hard_limit_state?.[e.slug],h=a?l?K`<span
            class="pill ${"applied"===l.status?"good":"high"}"
            title=${l.detail??l.status}
            ><span class="dot"></span>cap ${l.status}</span
          >`:K`<span class="pill medium" title="Configured; waiting for the Probe to apply"
            ><span class="dot"></span>cap pending</span
          >`:j;return K`
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
        ${s.enabled&&!1!==i.enabled?K`<span class="muted" style="font-size:11px;" title="Thresholds → action">
              ${r}%/${n}% → ${o}
            </span>`:K`<span class="muted" style="font-size:11px;">off</span>`}
        ${h}
        <button
          class="ha-btn"
          style="padding:2px 8px;font-size:11.5px;"
          @click=${()=>this._editSlug=this._editSlug===e.slug?null:e.slug}
        >
          ${this._editSlug===e.slug?"Close":"Edit"}
        </button>
      </div>
    `}_renderEditor(){const e=this._editSlug,t=this._watchdog,s=this._containers;if(!e||!t||!s)return j;const i=s.containers.find(t=>t.slug===e);if(!i)return j;const r=t.config.overrides?.[e]??{},n=t.config.hard_limits?.[e]??{memory_mb:null,cpus:null},o="addon"===i.kind;return K`
      <div
        style="border:1px solid var(--primary-color);border-radius:10px;padding:12px 14px;margin-top:10px;"
      >
        <div style="font-weight:600;font-size:13.5px;margin-bottom:8px;">
          ${i.name} <span class="muted" style="font-weight:400;">— per-container watchdog & cap</span>
        </div>
        <div class="toolbar" style="gap:14px;">
          <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
            CPU ≥
            <input type="number" min="10" max="100" style="width:64px;"
              placeholder=${String(t.config.default_cpu_percent)}
              .value=${null!=r.cpu_percent?String(r.cpu_percent):""}
              @change=${t=>{const s=t.target.value;this._setWatchdog({override:{slug:e,cpu_percent:s?Number(s):null}})}} />%
          </label>
          <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
            Memory ≥
            <input type="number" min="10" max="100" style="width:64px;"
              placeholder=${String(t.config.default_memory_percent)}
              .value=${null!=r.memory_percent?String(r.memory_percent):""}
              @change=${t=>{const s=t.target.value;this._setWatchdog({override:{slug:e,memory_percent:s?Number(s):null}})}} />%
          </label>
          ${o?K`
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Action
                  <select .value=${r.action??t.config.default_action}
                    @change=${t=>this._setWatchdog({override:{slug:e,action:t.target.value}})}>
                    <option value="alert" ?selected=${"alert"===(r.action??t.config.default_action)}>Alert only</option>
                    <option value="restart" ?selected=${"restart"===(r.action??t.config.default_action)}>Restart</option>
                    <option value="stop" ?selected=${"stop"===(r.action??t.config.default_action)}>Stop</option>
                  </select>
                </label>
              `:K`<span class="muted" style="font-size:12px;">action: alert only (never auto-restarted)</span>`}
          <button class="ha-btn" style="font-size:11.5px;" @click=${()=>this._setWatchdog({override:{slug:e,clear:!0}})}>
            Reset to defaults
          </button>
        </div>
        ${o?K`
              <div class="toolbar" style="gap:14px;margin-top:8px;margin-bottom:0;">
                <span style="font-size:12.5px;font-weight:600;">Hard cap (Docker):</span>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Memory
                  <input type="number" min="64" step="64" style="width:84px;" placeholder="unlimited"
                    .value=${null!=n.memory_mb?String(n.memory_mb):""}
                    @change=${t=>{const s=t.target.value;this._setWatchdog({hard_limit:{slug:e,memory_mb:s?Number(s):null,cpus:n.cpus}})}} /> MB
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  CPUs
                  <input type="number" min="0.1" step="0.1" style="width:70px;" placeholder="unlimited"
                    .value=${null!=n.cpus?String(n.cpus):""}
                    @change=${t=>{const s=t.target.value;this._setWatchdog({hard_limit:{slug:e,memory_mb:n.memory_mb,cpus:s?Number(s):null}})}} />
                </label>
                <button class="ha-btn" style="font-size:11.5px;"
                  @click=${()=>this._setWatchdog({hard_limit:{slug:e,memory_mb:null,cpus:null}})}>
                  Remove cap
                </button>
              </div>
              <p class="muted" style="font-size:11.5px;margin:6px 0 0;">
                ⚠ Hard caps are real Docker limits applied by the HA SOC Probe add-on. They
                require the Probe's <strong>Protection Mode to be disabled</strong> — a
                root-equivalent grant to that add-on (its security rating drops
                accordingly) — and are re-applied automatically every ~60s so they survive
                Supervisor recreating the container on updates. A memory cap means the
                kernel OOM-kills the add-on's process when it exceeds the cap — Supervisor's
                own add-on watchdog then restarts it if enabled.
              </p>
            `:j}
      </div>
    `}_renderWatchdogActivity(){const e=this._watchdog;if(!e)return j;const t=Object.entries(e.containers).filter(([,e])=>e.last_outcome).map(([e,t])=>({slug:e,text:t.last_outcome}));return t.length?K`
      <div style="margin-top:10px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          RECENT WATCHDOG ACTIVITY
        </div>
        ${t.map(e=>K`
            <div class="muted" style="font-size:12px;font-family:var(--ha-font-family-code, monospace);">
              ${e.slug}: ${e.text}
            </div>
          `)}
      </div>
    `:j}_classificationBadge(e){if(!e)return K`<span class="muted">—</span>`;return K`<span class="pill ${"clean_reboot"===e?"good":"kernel_fault"===e?"high":"medium"}"><span class="dot"></span>${"clean_reboot"===e?"clean reboot":"kernel_fault"===e?"kernel fault":"silent stop"}</span>`}_renderCrashForensics(){const e=this._crash;return K`
      <div class="card">
        <div class="toolbar">
          <h3 style="margin:0;flex:1;">Crash Forensics</h3>
          <button class="ha-btn" ?disabled=${this._crashLoading} @click=${()=>this._loadCrash()}>
            ${this._crashLoading?"Refreshing…":"Refresh"}
          </button>
        </div>
        <p class="muted" style="margin-top:-4px;font-size:12.5px;">
          A heartbeat file plus a clean-stop marker notice when the previous run stopped
          uncleanly — a silent host hang or kernel fault, not a logged Core crash — and
          auto-collect the previous boot's journal tail, Supervisor/host status, and
          container state into a bundle before the next boot's log churn rotates the
          evidence away. See docs/CRASH-FORENSICS.md.
        </p>

        ${this._crashLoading&&!e?K`<div class="empty">Loading crash forensics…</div>`:e?K`
                <div
                  style="border:1px solid var(--divider-color);border-radius:10px;padding:10px 14px;margin-bottom:12px;"
                >
                  <div class="toolbar" style="margin-bottom:0;">
                    <span style="font-weight:600;font-size:13.5px;">
                      Heartbeat ${e.enabled?"enabled":"disabled"}
                    </span>
                    <span class="muted" style="font-size:12px;">
                      ${e.enabled?`every ${e.heartbeat_interval_seconds}s`:"no automatic unclean-stop detection (owner-only setting)"}
                    </span>
                    <span class="spacer"></span>
                    ${e.last_check?.heartbeat?.ts?K`<span class="muted" style="font-size:12px;">
                          last heartbeat ${new Date(e.last_check.heartbeat.ts).toLocaleString()}
                        </span>`:K`<span class="muted" style="font-size:12px;">no heartbeat recorded yet</span>`}
                  </div>
                </div>

                <div class="toolbar" style="gap:10px;margin-bottom:10px;">
                  <button
                    class="ha-btn"
                    ?disabled=${!this._isOwner||this._crashCollecting}
                    @click=${()=>this._crashCollectNow()}
                  >
                    ${this._crashCollecting?"Collecting…":"Collect now (dry run)"}
                  </button>
                  ${this._isOwner?j:K`<span class="muted" style="font-size:12px;">Owner only.</span>`}
                  ${this._crashCollectResult?K`<span class="muted" style="font-size:12px;">
                        Bundle <code>${this._crashCollectResult.id}</code> collected
                        (${this._classificationBadge(this._crashCollectResult.classification)}).
                      </span>`:j}
                </div>

                ${this._crashError?K`<p style="color:var(--error-color,#db4437);font-size:12.5px;">${this._crashError}</p>`:j}
                ${this._crashFileError?K`<p style="color:var(--error-color,#db4437);font-size:12.5px;">${this._crashFileError}</p>`:j}
                ${this._crashFeedback?K`<p class="muted" style="font-size:12px;">${this._crashFeedback}</p>`:j}

                ${e.bundles.length?K`
                      <div style="overflow-x:auto;">
                        <table>
                          <thead>
                            <tr>
                              <th></th>
                              <th>Timestamp</th>
                              <th>Classification</th>
                              <th>Gap</th>
                              <th>Top suspects</th>
                              <th>Size</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${e.bundles.map(e=>this._renderCrashBundleRow(e))}
                          </tbody>
                        </table>
                      </div>
                    `:K`<div class="empty">
                      No unclean stops recorded since crash forensics was enabled.
                    </div>`}
              `:K`<div class="empty">
                ${this._crashError??"Crash forensics status isn't available right now."}
              </div>`}
      </div>
    `}_renderCrashBundleRow(e){const t=this._crashExpanded===e.id,s=e.suspects.slice(0,3);return K`
      <tr>
        <td>
          <button class="ha-btn" style="padding:2px 8px;font-size:11.5px;" @click=${()=>this._toggleCrashRow(e.id)}>
            ${t?"Close":"Expand"}
          </button>
        </td>
        <td class="muted" style="font-size:12px;">${e.ts?new Date(e.ts).toLocaleString():"—"}</td>
        <td>${this._classificationBadge(e.classification)}</td>
        <td class="num">${null!=e.gap_seconds?`${Math.round(e.gap_seconds)}s`:"—"}</td>
        <td style="font-size:12px;">
          ${s.length?s.map(e=>K`<div>${e.kind}: ${e.subject}</div>`):K`<span class="muted">none identified</span>`}
        </td>
        <td class="muted" style="font-size:12px;">${this._fmtBytes(e.size_bytes)}</td>
      </tr>
      ${t?K`
            <tr>
              <td colspan="6">${this._renderCrashBundleFiles(e)}</td>
            </tr>
          `:j}
    `}_renderCrashBundleFiles(e){return K`
      <div style="padding:8px 4px;">
        ${be.map(t=>{const s=`${e.id}/${t}`,i=this._crashFiles[s];return K`
            <div style="border:1px solid var(--divider-color);border-radius:8px;padding:8px 10px;margin-bottom:8px;">
              <div class="toolbar" style="margin-bottom:0;gap:8px;">
                <span style="font-family:var(--ha-font-family-code, monospace);font-size:12px;flex:1;">
                  ${t}
                </span>
                <button class="ha-btn" style="font-size:11.5px;" @click=${()=>this._viewCrashFile(e.id,t)}>
                  View
                </button>
                <button
                  class="ha-btn"
                  style="font-size:11.5px;"
                  @click=${()=>this._exportCrashFile(e.id,t,"copy")}
                >
                  Copy
                </button>
                <button
                  class="ha-btn"
                  style="font-size:11.5px;"
                  @click=${()=>this._exportCrashFile(e.id,t,"download")}
                >
                  Download
                </button>
              </div>
              ${void 0!==i?K`
                    <pre
                      style="max-height:280px;overflow:auto;font-size:11.5px;font-family:var(--ha-font-family-code, monospace);white-space:pre-wrap;word-break:break-word;margin:8px 0 0;"
                    >
${i.slice(0,5e4)}${i.length>5e4?"\n… (truncated in this view)":""}</pre
                    >
                  `:j}
            </div>
          `})}
      </div>
    `}_renderContainerRow(e){const t=e.flags.includes("high_memory"),s=e.flags.includes("high_cpu"),i="addon"===e.kind?"Add-on":"core"===e.kind?"Core":"Supervisor";return K`
      <tr>
        <td>
          <div style="font-weight:600;">${e.name}</div>
          <div class="muted" style="font-size:11.5px;">${i}${e.slug?` · ${e.slug}`:""}</div>
        </td>
        <td>
          ${"started"===e.state||"addon"!==e.kind?K`<span class="muted">running</span>`:K`<span class="pill high"><span class="dot"></span>${e.state??"stopped"}</span>`}
        </td>
        <td class="num">${this._pctCell(e.cpu_percent,s)}</td>
        <td class="num">${this._pctCell(e.memory_percent,t)}</td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(e.memory_usage)} / ${this._fmtBytes(e.memory_limit)}
        </td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(e.network_rx)} / ${this._fmtBytes(e.network_tx)}
        </td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(e.blk_read)} / ${this._fmtBytes(e.blk_write)}
        </td>
        <td>
          ${e.flags.length?K`<div class="chips">
                ${e.flags.map(e=>K`<span class="pill high"><span class="dot"></span>${"high_memory"===e?"high memory":"high_cpu"===e?"high CPU":e.replace("_"," ")}</span>`)}
              </div>`:K`<span class="muted">—</span>`}
        </td>
        <td>${this._wdCell(e)}</td>
      </tr>
    `}_renderRow(e){const t=e.github;return K`
      <tr>
        <td>
          <div style="font-weight:600;">${e.name}</div>
          <div class="muted" style="font-size:11.5px;">
            ${e.domain}${e.version?K` · v${e.version}`:""}
          </div>
          ${e.flags.length?K`<div class="chips" style="margin-top:3px;">
                ${e.flags.map(e=>K`<span class="pill high"><span class="dot"></span>${yi[e]??e}</span>`)}
              </div>`:j}
        </td>
        <td>
          <span class="pill ${vi[e.tier]}"><span class="dot"></span>${gi[e.tier]}</span>
        </td>
        <td class="muted">${e.quality_scale??"—"}</td>
        <td>
          ${null===e.license_present?K`<span class="muted">—</span>`:e.license_present?K`<span class="muted" title="License file present">yes</span>`:K`<span class="pill medium" title="No license file found"><span class="dot"></span>none</span>`}
        </td>
        <td>
          ${e.scanner_findings>0?K`<span class="pill high"><span class="dot"></span>${e.scanner_findings}</span>`:K`<span class="muted">0</span>`}
        </td>
        <td>
          ${t?null===t.commit_verified?K`<span class="muted">?</span>`:t.commit_verified?K`<span class="pill good" title="Default-branch head commit is signed/verified"
                    ><span class="dot"></span>signed</span
                  >`:K`<span class="muted" title="No verified signature on the head commit">unsigned</span>`:this._notCollected()}
        </td>
        <td>
          ${t?t.archived?K`<span class="pill high" title="Repository is archived"><span class="dot"></span>archived</span>`:null===t.has_release?K`<span class="muted">?</span>`:t.has_release?K`<span class="muted" title=${t.latest_release_tag??""}>tagged</span>`:K`<span class="pill medium" title="No published release — installs branch HEAD"
                      ><span class="dot"></span>branch</span
                    >`:this._notCollected()}
        </td>
        <td class="muted">${t?t.stars??"—":this._notCollected()}</td>
        <td class="muted" style="font-size:11.5px;">
          ${t?t.pushed_at?new Date(t.pushed_at).toLocaleDateString():"—":this._notCollected()}
        </td>
      </tr>
    `}};bi.styles=qe,bi.INTEGRATION_SORT={name:e=>e.name,tier:e=>mi[e.tier],quality:e=>e.quality_scale,license:e=>e.license_present,scanner:e=>e.scanner_findings,signed:e=>e.github?.commit_verified??null,release:e=>{const t=e.github;return t?t.archived?2:null===t.has_release?null:t.has_release?0:1:null},stars:e=>e.github?.stars??null,pushed:e=>e.github?.pushed_at??null},bi.CONTAINER_SORT={name:e=>e.name,state:e=>"started"===e.state||"addon"!==e.kind?"running":e.state??"stopped",cpu:e=>e.cpu_percent,memory:e=>e.memory_percent,usage:e=>e.memory_usage,net:e=>null==e.network_rx&&null==e.network_tx?null:(e.network_rx??0)+(e.network_tx??0),disk:e=>null==e.blk_read&&null==e.blk_write?null:(e.blk_read??0)+(e.blk_write??0),flags:e=>e.flags.length},bi.HACS_SORT={name:e=>e.full_name,category:e=>e.category,installed:e=>e.installed_version,available:e=>e.available_version,author:e=>e.authors.length?e.authors.join(", "):null,updated:e=>e.last_updated},e([pe()],bi.prototype,"_overview",void 0),e([pe()],bi.prototype,"_loading",void 0),e([pe()],bi.prototype,"_error",void 0),e([pe()],bi.prototype,"_refreshing",void 0),e([pe()],bi.prototype,"_search",void 0),e([pe()],bi.prototype,"_tierFilter",void 0),e([pe()],bi.prototype,"_limit",void 0),e([pe()],bi.prototype,"_intSort",void 0),e([pe()],bi.prototype,"_containerSort",void 0),e([pe()],bi.prototype,"_containers",void 0),e([pe()],bi.prototype,"_containersLoading",void 0),e([pe()],bi.prototype,"_watchdog",void 0),e([pe()],bi.prototype,"_editSlug",void 0),e([pe()],bi.prototype,"_wdError",void 0),e([pe()],bi.prototype,"_hacs",void 0),e([pe()],bi.prototype,"_hacsBusy",void 0),e([pe()],bi.prototype,"_hacsError",void 0),e([pe()],bi.prototype,"_hacsRefresh",void 0),e([pe()],bi.prototype,"_hacsUpdate",void 0),e([pe()],bi.prototype,"_hacsSort",void 0),e([pe()],bi.prototype,"_hacsCategoryFilter",void 0),e([pe()],bi.prototype,"_hacsOwnerFilter",void 0),e([pe()],bi.prototype,"_isOwner",void 0),e([pe()],bi.prototype,"_crash",void 0),e([pe()],bi.prototype,"_crashLoading",void 0),e([pe()],bi.prototype,"_crashError",void 0),e([pe()],bi.prototype,"_crashExpanded",void 0),e([pe()],bi.prototype,"_crashFiles",void 0),e([pe()],bi.prototype,"_crashFileError",void 0),e([pe()],bi.prototype,"_crashCollecting",void 0),e([pe()],bi.prototype,"_crashCollectResult",void 0),e([pe()],bi.prototype,"_crashFeedback",void 0),bi=fi=e([he("ha-soc-integration-security-view")],bi);const wi=1048576,Si=e=>new Date(e).toLocaleString(),xi=[{domain:"lock",label:"Lock entities (any integration)"},{domain:"siren",label:"Siren entities (any integration)"},{domain:"valve",label:"Valve entities (any integration)"}],$i=[{domain:"kidde_homesafe",label:"Kidde HomeSafe"},{domain:"elkm1",label:"Elk-M1 Security"},{domain:"unifiprotect",label:"UniFi Protect"},{domain:"keymaster",label:"Keymaster"},{domain:"emporia_vue",label:"Emporia Vue"}],ki={brute_force_ip:"Brute force (per source IP)",success_after_failures:"Success after failed logins",new_ip_login:"Login from a new network",off_hours_anomaly:"Off-hours activity burst",dormant_revival:"Dormant account revival",mass_entity_burst:"Mass entity control burst",token_minting_anomaly:"Token minting anomaly",disabled_user_activity:"Disabled-user activity",privilege_escalation:"Privilege escalation"};let Ci=class extends ae{constructor(){super(...arguments),this._settings=null,this._security=null,this._thresholds=null,this._loading=!0,this._error=null,this._closedCards=new Set,this._connectionTests=new Map,this._probeRestart=new Map,this._discoverCandidates=new Map}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{this._settings=await(e=this.hass,we(e,{type:"ha_soc/settings/get"}));try{this._security=await Fe(this.hass)}catch{this._security=null}try{this._thresholds=await Ce(this.hass)}catch{this._thresholds=null}}catch(e){this._error=e?.message??String(e)}finally{this._loading=!1}var e}async _updateThreshold(e,t,s){await We(this.hass,{detection_thresholds:{[e]:{[t]:s}}}),this._thresholds=await Ce(this.hass)}async _resetThresholds(){var e;this._thresholds=await(e=this.hass,we(e,{type:"ha_soc/detections/thresholds_reset"}).then(e=>e.rules))}async _update(e,t){if(!this._settings)return;const s=this._settings;this._settings={...this._settings,[e]:t};try{this._settings=await We(this.hass,{[e]:t})}catch(e){throw this._settings=s,e}}_cardStorageKey(e){return`ha-soc-settings-card-open:${e}`}_isOpen(e){if(this._closedCards.has(e))return!1;try{if("false"===localStorage.getItem(this._cardStorageKey(e)))return this._closedCards.add(e),!1}catch{}return!0}_onToggle(e,t){const s=t.target.open;s?this._closedCards.delete(e):this._closedCards.add(e);try{localStorage.setItem(this._cardStorageKey(e),String(s))}catch{}}_statusPill(e,t){let s=!1,i=!1,r="var(--status-critical)",n="not configured";return"unifi_network"===t?(s=!!e.unifi_network_host,i=!!e.unifi_network_api_key_set):"unifi_protect"===t?(s=!!e.unifi_protect_host,i=!!e.unifi_protect_api_key_set):"pihole"===t?(s=!!e.pihole_host,i=!!e.pihole_api_key_set):"technitium"===t?(s=!!e.technitium_host,i=!!e.technitium_api_token_set):"snmpv3"===t&&(s=!!e.snmp_listen_address&&!!e.snmp_username,i=!!e.snmp_auth_passphrase_set&&!!e.snmp_priv_passphrase_set),s&&i?(r="var(--status-good)",n="configured","snmpv3"===t&&e.snmp_status&&(e.snmp_status.error?(r="var(--status-critical)",n="error"):e.snmp_status.running?(r="var(--status-good)",n="running"):(r="var(--status-warning)",n=e.snmp_status.enabled?"waiting":"disabled"))):(s||i)&&(r="var(--status-warning)",n="partially configured"),K`<span class="pill" style="background:none;" title=${n}
      ><span class="dot" style="background:${r};"></span>${n}</span
    >`}async _testConnection(e){let t;this._connectionTests=new Map(this._connectionTests).set(e,"pending");try{t="unifi_network"===e?await(s=this.hass,we(s,{type:"ha_soc/unifi_network/test_connection"})):"unifi_protect"===e?await(e=>we(e,{type:"ha_soc/unifi_protect/test_connection"}))(this.hass):"pihole"===e?await(e=>we(e,{type:"ha_soc/pihole/test_connection"}))(this.hass):await(e=>we(e,{type:"ha_soc/technitium/test_connection"}))(this.hass)}catch(e){t={ok:!1,reachable:!1,error:e?.message??String(e)}}var s;this._connectionTests=new Map(this._connectionTests).set(e,t)}_renderTestConnection(e){const t=this._connectionTests.get(e),s="pending"===t;let i=K``;return t&&"pending"!==t&&(i=t.reachable?K`<span style="color:var(--status-good);font-size:12.5px;margin-left:8px;">&#x2713; Reachable</span>`:K`<span style="color:var(--status-critical);font-size:12.5px;margin-left:8px;"
            >&#x2717; ${t.error??"unreachable"}</span
          >`),K`
      <div class="settings-row">
        <button class="ha-btn" ?disabled=${s} @click=${()=>this._testConnection(e)}>
          ${s?"Testing…":"Test connection"}
        </button>
        ${i}
      </div>
    `}async _restartProbe(){let e;this._probeRestart=new Map(this._probeRestart).set("probe","pending");try{e=await(t=this.hass,we(t,{type:"ha_soc/probe/restart"}))}catch(t){e={ok:!1,reason:"restart_failed",error:t?.message??String(t)}}var t;this._probeRestart=new Map(this._probeRestart).set("probe",e)}_renderProbeRestart(){const e=this._probeRestart.get("probe"),t="pending"===e;let s=K``;return e&&"pending"!==e&&(s=e.ok?K`<span style="color:var(--status-good);font-size:12.5px;"
            >&#x2713; Restart requested</span
          >`:K`<span style="color:var(--status-critical);font-size:12.5px;"
            >&#x2717; ${e.error??e.reason??"restart failed"}</span
          >`),K`
      <div class="probe-error-actions">
        <button class="ha-btn" ?disabled=${t} @click=${()=>this._restartProbe()}>
          ${t?"Restarting…":"Restart Probe add-on"}
        </button>
        <span class="muted" style="font-size:12px;"
          >Or restart it yourself: Settings → Add-ons → HA SOC Probe → Restart.</span
        >
        ${s}
      </div>
    `}async _discover(e){this._discoverCandidates=new Map(this._discoverCandidates).set(e,"pending");try{const s=await(t=this.hass,we(t,{type:"ha_soc/containers/discover_candidates"}));this._discoverCandidates=new Map(this._discoverCandidates).set(e,s[e])}catch{this._discoverCandidates=new Map(this._discoverCandidates).set(e,[])}var t}_renderDiscover(e,t){const s=this._discoverCandidates.get(e),i="pending"===s;let r=K``;return s&&"pending"!==s&&(r=0===s.length?K`<div class="muted" style="font-size:11.5px;margin-top:4px;">
          No candidates found — run a network scan from the Scanner tab first, or make sure
          Network Scan is enabled in Settings.
        </div>`:K`
          <div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:6px;">
            ${s.map(e=>K`
                <span
                  class="pill clickable"
                  style="background:none;cursor:pointer;"
                  title="Confidence: ${e.confidence}"
                  @click=${()=>this._update(t,e.ip)}
                  >${e.ip} <span class="muted" style="font-size:10.5px;">(${e.confidence})</span></span
                >
              `)}
          </div>
        `),K`
      <div style="margin-top:4px;">
        <button class="ha-btn" ?disabled=${i} @click=${()=>this._discover(e)}>
          ${i?"Discovering…":"Discover"}
        </button>
        ${r}
      </div>
    `}_updateSecuritySource(e,t){this._settings&&this._update("security_sources_enabled",{...this._settings.security_sources_enabled,[e]:t})}_renderSecretField(e,t,s){return K`
      <label class="settings-row">
        <span>${e}</span>
        <input
          type="password"
          placeholder=${s?"configured — type to replace":"unset"}
          @change=${e=>{const s=e.target.value;this._update(t,s||null)}}
        />
      </label>
    `}_renderIntegrationRow(e,t){const s=this._settings,i=this._security?.integrations.filter(t=>t.domain===e)??[],r=i.some(e=>e.installed),n=i.some(e=>e.installed&&"loaded"!==e.state),o=i.find(e=>e.installed)?.entry_id??null,a=r?n?i.find(e=>"loaded"!==e.state).state:"loaded":"not installed";return K`
      <div class="settings-row">
        <span>${t}</span>
        <span
          class="muted ${r&&o?"clickable":""}"
          style="font-size:12px;${n?"color:var(--error-color,#db4437);":""}"
          title=${r&&o?"View in Home Assistant's Devices page":""}
          @click=${()=>r&&o&&ge(ve(o))}
          >${a}</span
        >
        <input
          type="checkbox"
          .checked=${s.security_sources_enabled?.[e]??!0}
          @change=${t=>this._updateSecuritySource(e,t.target.checked)}
        />
      </div>
    `}_renderThresholdsCard(e){return K`
      <details class="card" ?open=${this._isOpen("detection-thresholds")} @toggle=${e=>this._onToggle("detection-thresholds",e)}>
        <summary class="card-summary"><h3>Detection Thresholds</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every detection rule's tunable parameters, each accepted only within the
          range shown. The secure defaults are the most sensitive values that do not
          alert on ordinary same-network activity - they miss the fewest attacks, at
          the cost of more alerts. Changes apply from the next analysis pass and are
          audited with a per-field diff.
        </p>
        <label class="settings-row">
          <span>
            Evidence retention (days)
            <span class="muted" style="display:block;font-size:11.5px;"
              >Resolved detections and resolved/dismissed findings older than this are
              pruned; open and acknowledged items never expire.</span
            >
          </span>
          <input
            type="number"
            min="30"
            max="3650"
            .value=${String(e.evidence_retention_days)}
            @change=${e=>this._update("evidence_retention_days",Number(e.target.value))}
          />
        </label>
        ${this._thresholds?Object.entries(this._thresholds).map(([e,t])=>K`
                <h4
                  style="margin:16px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:0.03em;color:var(--secondary-text-color);"
                >
                  ${ki[e]??e}
                </h4>
                ${Object.entries(t).map(([t,s])=>"bool"===s.type?K`
                        <label class="settings-row">
                          <span>
                            ${t}
                            <span class="muted" style="display:block;font-size:11.5px;"
                              >secure default: ${s.default?"on":"off"}</span
                            >
                          </span>
                          <input
                            type="checkbox"
                            .checked=${Boolean(s.value)}
                            @change=${s=>this._updateThreshold(e,t,s.target.checked)}
                          />
                        </label>
                      `:K`
                        <label class="settings-row">
                          <span>
                            ${t}
                            <span class="muted" style="display:block;font-size:11.5px;"
                              >${s.min} to ${s.max}, secure default ${s.default}</span
                            >
                          </span>
                          <input
                            type="number"
                            min=${String(s.min)}
                            max=${String(s.max)}
                            step=${"float"===s.type?"any":"1"}
                            .value=${String(s.value)}
                            @change=${s=>this._updateThreshold(e,t,Number(s.target.value))}
                          />
                        </label>
                      `)}
              `):K`<p class="muted" style="font-size:12.5px;">Could not load the threshold table.</p>`}
        <div class="toolbar" style="margin-top:12px;">
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._resetThresholds}>Reset to secure defaults</button>
        </div>
      </details>
    `}render(){if(this._loading)return K`<div class="empty">Loading settings…</div>`;if(this._error||!this._settings)return K`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Settings</h3>
          <p style="font-size:13px;">${this._error??"The server returned no settings."}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const e=this._settings;return K`
      ${e.github_token_set?"":K`
            <div
              style="background:#fdf6d8;color:#6b5300;border:1px solid #e8d071;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13.5px;line-height:1.5;"
            >
              <strong>No GitHub API key configured.</strong> The Integration Security tab
              can still classify every integration and run local checks, but the
              GitHub-derived provenance signals — release vs. branch, identity assurance,
              maintenance recency, popularity, and archived status — stay
              <em>“not collected”</em> until a token is set below. A token also raises
              GitHub's rate limit from 60 to 5,000 requests/hour.
            </div>
          `}

      <div class="settings-grid">
        <div class="card" style="grid-column:1/-1;">
          <div class="settings-row" style="border-bottom:none;padding-top:0;">
            <span>
              <h3 style="margin:0;">External Connections</h3>
              <span class="muted" style="display:block;font-size:11.5px;margin-top:4px;"
                >Informational master switch for this phase only — it does not gate any
                integration's runtime behavior yet.
                ${e.external_connections_changed_at?K`${e.external_connections_enabled?"Enabled":"Disabled"}
                    ${Si(e.external_connections_changed_at)}`:"never changed"}</span
              >
            </span>
            <label style="display:flex;align-items:center;gap:6px;">
              <span>Enable external connections</span>
              <input
                type="checkbox"
                .checked=${e.external_connections_enabled}
                @change=${e=>this._update("external_connections_enabled",e.target.checked)}
              />
            </label>
          </div>
        </div>

      <details class="card" ?open=${this._isOpen("access-control")} @toggle=${e=>this._onToggle("access-control",e)}>
        <summary class="card-summary"><h3>Access Control</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Checked server-side on every
          <code>ha_soc/*</code> command, not just on whether the panel is visible in the
          sidebar — a locked-out admin still sees the SOC panel entry (Home Assistant's
          sidebar has no finer-grained hook than admin/non-admin) but every request it
          makes is rejected until this is opened up.
        </p>
        <label class="settings-row">
          <span>Who can use this panel</span>
          <select
            .value=${e.access_level}
            @change=${e=>this._update("access_level",e.target.value)}
          >
            <option value="owner_only">Account owner only</option>
            <option value="owner_and_admins">Owner and all administrators</option>
          </select>
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("mfa-policy")} @toggle=${e=>this._onToggle("mfa-policy",e)}>
        <summary class="card-summary"><h3>MFA Non-Compliance Policy</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant core has no hook to <em>require</em> a second factor at login —
          this can only ever <span class="tag cosmetic">audit</span> that gap, or take the
          one real action core does expose:
          <span class="tag enforced">enforced</span> deactivating an admin account that
          stays out of compliance past the grace period below. The account owner is never
          evaluated or deactivated by this policy.
        </p>
        <label class="settings-row">
          <span>Policy for admins without MFA enabled</span>
          <select
            .value=${e.mfa_policy}
            @change=${e=>this._update("mfa_policy",e.target.value)}
          >
            <option value="audit_only">Audit only — flag via Repairs, never act</option>
            <option value="auto_deactivate">Deactivate after grace period</option>
          </select>
        </label>
        <label class="settings-row">
          <span>Grace period (days)</span>
          <input
            type="number"
            min="1"
            max="365"
            .value=${String(e.mfa_grace_period_days)}
            ?disabled=${"auto_deactivate"!==e.mfa_policy}
            @change=${e=>this._update("mfa_grace_period_days",Number(e.target.value))}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("vulnerability-scanning")} @toggle=${e=>this._onToggle("vulnerability-scanning",e)}>
        <summary class="card-summary"><h3>Device Vulnerability Scanning</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">best-effort</span> CVE correlation is a heuristic
          vendor/model match against NVD, not a confirmed exploit — absence of a match is
          not evidence a device is secure.
        </p>
        <label class="settings-row">
          <span>
            Look up device CVEs against NIST's NVD
            <span class="muted" style="display:block;font-size:11.5px;"
              >While on, device manufacturer and model strings are sent to
              NIST's NVD (the U.S. National Vulnerability Database) to find
              candidate CVEs. Turning this off stops that lookup entirely.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.nvd_lookups_enabled}
            @change=${e=>this._update("nvd_lookups_enabled",e.target.checked)}
          />
        </label>
        ${this._renderSecretField("NVD API key (optional — raises the public rate limit)","nvd_api_key",!!e.nvd_api_key_set)}
      </details>

      ${this._renderThresholdsCard(e)}

      <details class="card" ?open=${this._isOpen("integration-security-provenance")} @toggle=${e=>this._onToggle("integration-security-provenance",e)}>
        <summary class="card-summary"><h3>Integration Security (Provenance)</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A <strong>provenance</strong> signal, not a safety verdict — it reflects how much
          is known about where an integration's code comes from, never that the code is safe
          to run. A GitHub token (a fine-grained token with public read access is enough)
          lets the Integration Security tab collect release, signing, maintenance,
          popularity, and archived-status signals for integrations with a known GitHub repo.
        </p>
        ${this._renderSecretField("GitHub API token (optional)","github_token",!!e.github_token_set)}
      </details>

      <details class="card" ?open=${this._isOpen("unifi-network")} @toggle=${e=>this._onToggle("unifi-network",e)}>
        <summary class="card-summary"><h3>UniFi Network</h3>${this._statusPill(e,"unifi_network")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a UniFi console over your LAN with a
          <strong>local API key</strong> (UniFi OS → Settings → Control Plane →
          Integrations) to populate the <strong>Network</strong> tab — status, WAN
          throughput, clients, and network devices. Read-only with this key; nothing is
          changed on the controller unless write-back below is enabled with its own key, and
          no data leaves your network.
        </p>
        ${this._renderTestConnection("unifi_network")}
        <label class="settings-row">
          <span>Controller host or IP</span>
          <input
            type="text"
            placeholder="e.g. 192.168.1.1"
            .value=${e.unifi_network_host??""}
            @change=${e=>{const t=e.target.value.trim();this._update("unifi_network_host",t||null)}}
          />
        </label>
        ${this._renderSecretField("Local API key","unifi_network_api_key",!!e.unifi_network_api_key_set)}
        <label class="settings-row">
          <span>
            <span class="tag enforced">enforced</span> Allow suggestion write-back
            <span class="muted" style="display:block;font-size:11.5px;"
              >Lets the owner apply a Network Security suggestion (disable a broad ACL rule or
              Firewall Policy) from the panel. Uses the separate write key below, never the
              read key; each apply is audited and read back from the controller. Off by
              default.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.unifi_network_write_enabled}
            @change=${e=>this._update("unifi_network_write_enabled",e.target.checked)}
          />
        </label>
        ${this._renderSecretField("Write-scoped API key (write-back only)","unifi_network_write_api_key",!!e.unifi_network_write_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — UniFi consoles ship a self-signed certificate.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.unifi_network_verify_ssl}
            @change=${e=>this._update("unifi_network_verify_ssl",e.target.checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("unifi-protect")} @toggle=${e=>this._onToggle("unifi-protect",e)}>
        <summary class="card-summary"><h3>UniFi Protect</h3>${this._statusPill(e,"unifi_protect")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A second local API key for a UniFi Protect console, surfaced as a compact
          camera-status card on the Network tab. Same local-only, read-only posture as
          Network above.
        </p>
        ${this._renderTestConnection("unifi_protect")}
        <label class="settings-row">
          <span>Protect host or IP</span>
          <input
            type="text"
            placeholder="e.g. 192.168.1.1"
            .value=${e.unifi_protect_host??""}
            @change=${e=>{const t=e.target.value.trim();this._update("unifi_protect_host",t||null)}}
          />
        </label>
        ${this._renderSecretField("Local API key","unifi_protect_api_key",!!e.unifi_protect_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — UniFi consoles ship a self-signed certificate.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.unifi_protect_verify_ssl}
            @change=${e=>this._update("unifi_protect_verify_ssl",e.target.checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("pihole")} @toggle=${e=>this._onToggle("pihole",e)}>
        <summary class="card-summary"><h3>Pi-hole</h3>${this._statusPill(e,"pihole")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a Pi-hole v6 instance over your LAN with its
          <strong>app password</strong> (Pi-hole → Settings → API → App password) to
          populate the <strong>Network Security</strong> tab's DNS section — blocking
          status, query totals, and whether the IoT subnet below has its own Pi-hole
          client group. Read-only; nothing is ever toggled or reassigned on Pi-hole.
        </p>
        ${this._renderTestConnection("pihole")}
        <label class="settings-row">
          <span>Pi-hole host or IP</span>
          <input
            type="text"
            placeholder="e.g. pi.hole or 192.168.1.5"
            .value=${e.pihole_host??""}
            @change=${e=>{const t=e.target.value.trim();this._update("pihole_host",t||null)}}
          />
        </label>
        ${this._renderDiscover("pihole","pihole_host")}
        ${this._renderSecretField("App password","pihole_api_key",!!e.pihole_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — most home Pi-hole instances are plain HTTP on the LAN.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.pihole_verify_ssl}
            @change=${e=>this._update("pihole_verify_ssl",e.target.checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            IoT network CIDR
            <span class="muted" style="display:block;font-size:11.5px;"
              >The subnet whose DNS your UniFi gateway forwards to Pi-hole, e.g.
              192.168.50.0/24. Used only to check whether it has a dedicated Pi-hole
              client group — never to configure DNS itself.</span
            >
          </span>
          <input
            type="text"
            placeholder="e.g. 192.168.50.0/24"
            .value=${e.pihole_iot_cidr??""}
            @change=${e=>{const t=e.target.value.trim();this._update("pihole_iot_cidr",t||null)}}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("technitium")} @toggle=${e=>this._onToggle("technitium",e)}>
        <summary class="card-summary"><h3>Technitium DNS Server</h3>${this._statusPill(e,"technitium")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a Technitium DNS Server instance over your LAN with an
          <strong>API token</strong> (Technitium → Administration → Sessions → Create token) to
          populate the <strong>Network Security</strong> tab's DNS section — blocking
          status, query totals, and the zone/record inventory. Read-only; nothing is ever
          toggled or edited on Technitium. Independent of Pi-hole above — configure either,
          both, or neither.
        </p>
        ${this._renderTestConnection("technitium")}
        <label class="settings-row">
          <span>Technitium host or IP</span>
          <input
            type="text"
            placeholder="e.g. dns.local or 192.168.1.6"
            .value=${e.technitium_host??""}
            @change=${e=>{const t=e.target.value.trim();this._update("technitium_host",t||null)}}
          />
        </label>
        ${this._renderDiscover("technitium","technitium_host")}
        ${this._renderSecretField("API token","technitium_api_token",!!e.technitium_api_token_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — most home Technitium instances are plain HTTP on the LAN.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.technitium_verify_ssl}
            @change=${e=>this._update("technitium_verify_ssl",e.target.checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("integration-security-scanner")} @toggle=${e=>this._onToggle("integration-security-scanner",e)}>
        <summary class="card-summary"><h3>Integration Security Scanner</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static analysis of every installed integration's source, run on the weekly
          sweep below or on demand from the Scanner tab.
        </p>
        <label class="settings-row">
          <span>Run the weekly scan automatically</span>
          <input
            type="checkbox"
            .checked=${e.scanner_enabled}
            @change=${e=>this._update("scanner_enabled",e.target.checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            Include network-reachability checks
            <span class="muted" style="display:block;font-size:11.5px;"
              >Best-effort connectivity probes against configured device hosts — off by
              default since it makes outbound requests.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.scanner_network_checks_enabled}
            @change=${e=>this._update("scanner_network_checks_enabled",e.target.checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("unused-installs")} @toggle=${e=>this._onToggle("unused-installs",e)}>
        <summary class="card-summary"><h3>Unused Installs</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Informational hygiene checks for code that is present but that nothing uses:
          custom integrations with no config entry, entries with no entities, HACS
          downloads that never load, and dashboard resources no dashboard references.
        </p>
        <label class="settings-row">
          <span>
            Scan YAML-mode dashboard files
            <span class="muted" style="display:block;font-size:11.5px;"
              >Reads each YAML dashboard through Home Assistant's own loader so cards in
              included files count as used. Only card types are read; nothing is written.
              Off by default because it reads files from the configuration directory. With
              it off, the unused-resource check cannot evaluate while any YAML dashboard
              exists.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.hygiene_scan_yaml_dashboards}
            @change=${e=>this._update("hygiene_scan_yaml_dashboards",e.target.checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("dashboard-files")} @toggle=${e=>this._onToggle("dashboard-files",e)}>
        <summary class="card-summary"><h3>Dashboard Files</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Lets administrators edit the YAML files under the configuration directory's
          <code>dashboards</code> folder from the Assets workspace. No other directory is
          reachable, files can only be modified (never created, renamed, or deleted), and
          every write is backed up and audited with the reason the operator gave.
        </p>
        <label class="settings-row">
          <span>
            Allow editing dashboard YAML files
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default. While it is off the panel shows nothing and the server
              refuses every read and write, whichever access level is set. While it is on,
              who may edit still follows the SOC access level: owner only, or owner and
              administrators.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.dashboard_edit_enabled}
            @change=${e=>this._update("dashboard_edit_enabled",e.target.checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("device-ssh")} @toggle=${e=>this._onToggle("device-ssh",e)}>
        <summary class="card-summary"><h3>Device SSH Collection</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Lets HA SOC open read-only SSH sessions to UniFi devices using a keypair the
          controller distributes to every adopted device. Commands come from a fixed
          allowlist in the integration; nothing configures or restarts a device. Used for
          the facts the UniFi API does not expose at any endpoint, such as per-port VLAN
          handling and the inform URL a device actually holds.
        </p>
        <label class="settings-row">
          <span>
            Allow read-only SSH to devices
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default. While it is off the server refuses every run. Generate the
              keypair and paste the public key into the controller under Device
              Authentication, SSH Keys, then wait for the devices to re-provision.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.ssh_collection_enabled}
            @change=${e=>this._update("ssh_collection_enabled",e.target.checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            Device SSH username
            <span class="muted" style="display:block;font-size:11.5px;"
              >The site-wide account set in the controller's Device Authentication panel.</span
            >
          </span>
          <input
            type="text"
            .value=${e.ssh_username||""}
            @change=${e=>this._update("ssh_username",e.target.value||null)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("audit-log")} @toggle=${e=>this._onToggle("audit-log",e)}>
        <summary class="card-summary"><h3>Audit Log</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Hash-chained JSONL, rotated on
          whichever of these two limits is hit first — see the Audit Log tab's
          <code>Verify chain</code> action.
        </p>
        <label class="settings-row">
          <span>Retention (days)</span>
          <input
            type="number"
            min="7"
            max="3650"
            .value=${String(e.audit_retention_days)}
            @change=${e=>this._update("audit_retention_days",Number(e.target.value))}
          />
        </label>
        <label class="settings-row">
          <span>Maximum size (MB)</span>
          <input
            type="number"
            min="1"
            .value=${String(Math.round(e.audit_max_bytes/wi))}
            @change=${e=>this._update("audit_max_bytes",Math.round(Number(e.target.value)*wi))}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("siem-syslog")} @toggle=${e=>this._onToggle("siem-syslog",e)}>
        <summary class="card-summary"><h3>SIEM / Syslog Export</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Exports finalized hash-chained audit records as RFC 5424 with JSON or
          CEF 0, or as bare canonical JSON for collectors that explicitly require
          it. TCP and TLS retain RFC 6587 octet framing. This stays disabled until
          a destination is configured.
        </p>
        <label class="settings-row">
          <span>
            Payload format
            <span class="muted" style="display:block;font-size:11.5px;"
              >Independent of the UDP, TCP, or TLS transport below.</span
            >
          </span>
          <select
            .value=${e.syslog_format}
            @change=${e=>this._update("syslog_format",e.target.value)}
          >
            <option value="rfc5424_json">RFC 5424 + Raw audit JSON (default)</option>
            <option value="cef">RFC 5424 + CEF 0</option>
            <option value="raw_json">Bare Raw JSON (collector compatibility)</option>
          </select>
        </label>
        ${"raw_json"===e.syslog_format?K`<p class="muted" style="font-size:12px;color:var(--warning-color,#ffa600);">
              Bare Raw JSON has no RFC 5424 envelope. Use it only when the receiver
              explicitly requires JSON-only input; RFC 5424 + JSON remains the
              standards-based default.
            </p>`:""}
        <label class="settings-row">
          <span>Transport</span>
          <select
            .value=${e.syslog_transport}
            @change=${e=>this._update("syslog_transport",e.target.value)}
          >
            <option value="disabled">Disabled</option>
            <option value="udp">UDP (unencrypted fallback)</option>
            <option value="tcp">TCP (unencrypted fallback)</option>
            <option value="tls">TLS over TCP</option>
          </select>
        </label>
        ${"udp"===e.syslog_transport||"tcp"===e.syslog_transport?K`<p class="muted" style="font-size:12px;color:var(--warning-color,#ffa600);">
              UDP/TCP Syslog is unencrypted. Restrict it to a dedicated management
              VLAN or VPN path and migrate to TLS when certificates are assigned.
            </p>`:""}
        <label class="settings-row">
          <span>SIEM host or IP</span>
          <input
            type="text"
            placeholder="e.g. sem.example.lan"
            .value=${e.syslog_host??""}
            @change=${e=>{const t=e.target.value.trim();this._update("syslog_host",t||null)}}
          />
        </label>
        <label class="settings-row">
          <span>Port <span class="muted" style="display:block;font-size:11.5px;">Common: 514 UDP/TCP, 6514 TLS</span></span>
          <input
            type="number"
            min="1"
            max="65535"
            .value=${String(e.syslog_port)}
            @change=${e=>this._update("syslog_port",Number(e.target.value))}
          />
        </label>
        <label class="settings-row">
          <span>Facility</span>
          <select
            .value=${String(e.syslog_facility)}
            @change=${e=>this._update("syslog_facility",Number(e.target.value))}
          >
            ${Array.from({length:8},(e,t)=>K`<option value=${String(16+t)}>local${t}</option>`)}
          </select>
        </label>
        ${"tls"===e.syslog_transport?K`<label class="settings-row">
              <span>
                Verify SIEM TLS certificate
                <span class="muted" style="display:block;font-size:11.5px;"
                  >On by default. Turn off only while the receiver uses a self-signed
                  certificate, then re-enable after certificate assignment.</span
                >
              </span>
              <input
                type="checkbox"
                .checked=${e.syslog_tls_verify}
                @change=${e=>this._update("syslog_tls_verify",e.target.checked)}
              />
            </label>`:""}
        ${e.syslog_status?K`<p class="muted" style="font-size:12px;">
              Status: ${e.syslog_status.last_error?`error — ${e.syslog_status.last_error}`:e.syslog_status.connected?"connected":e.syslog_status.enabled?"waiting for first delivery":"disabled"}.
              Sent ${e.syslog_status.sent}; queued ${e.syslog_status.queued}; dropped
              ${e.syslog_status.dropped}. Format ${e.syslog_status.format}.
            </p>`:""}

        <div class="syslog-subsection-divider" role="separator"></div>
        <h4 class="syslog-subsection-heading">Syslog Receiver (opposite direction)</h4>
        <p class="muted" style="margin-top:-4px;font-size:12.5px;">
          Receives forwarded logs over UDP instead of sending HA SOC's own audit
          records out — compatible with the "logspout" HA add-on, which forwards
          every Docker container's stdout/stderr on this host. UDP only this
          phase; TCP/TLS receive is a documented follow-up. Point logspout's
          <code>syslog+udp://</code> target at this host and the port below.
        </p>
        <label class="settings-row">
          <span>Enable syslog receiver</span>
          <input
            type="checkbox"
            .checked=${e.syslog_receiver_enabled}
            @change=${e=>this._update("syslog_receiver_enabled",e.target.checked)}
          />
        </label>
        <label class="settings-row">
          <span
            >Listen port
            <span class="muted" style="display:block;font-size:11.5px;"
              >Distinct from the exporter's port above and from SNMP's; the HA SOC
              Probe add-on binds this port (host networking).</span
            ></span
          >
          <input
            type="number"
            min="1"
            max="65535"
            .value=${String(e.syslog_receiver_port)}
            @change=${e=>this._update("syslog_receiver_port",Number(e.target.value))}
          />
        </label>
        ${e.syslog_receiver_status?K`<p class="muted" style="font-size:12px;">
              Status: ${e.syslog_receiver_status.error?`error — ${e.syslog_receiver_status.error}`:e.syslog_receiver_status.running?"listening":e.syslog_receiver_status.enabled?"starting":"disabled"}.
              ${null!=e.syslog_receiver_status.entry_count?K`Buffered ${e.syslog_receiver_status.entry_count} entries.`:""}
              ${e.syslog_receiver_status.last_received_at?K`Last received ${e.syslog_receiver_status.last_received_at}.`:""}
            </p>`:""}
      </details>

      <details class="card" ?open=${this._isOpen("security-integrations-health")} @toggle=${e=>this._onToggle("security-integrations-health",e)}>
        <summary class="card-summary"><h3>Security Integrations Health</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          What shows up in the always-present Dashboard security card. A source stays on
          by default — a device or integration you haven't installed just reports "not
          installed" rather than being hidden, and turning a toggle off here only affects
          this dashboard section, nothing else.
        </p>
        ${xi.map(({domain:t,label:s})=>K`
            <label class="settings-row">
              <span>${s}</span>
              <input
                type="checkbox"
                .checked=${e.security_sources_enabled?.[t]??!0}
                @change=${e=>this._updateSecuritySource(t,e.target.checked)}
              />
            </label>
          `)}
        <h4 style="margin:16px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:0.03em;color:var(--secondary-text-color);">
          Integrations Loaded
        </h4>
        ${$i.map(({domain:e,label:t})=>this._renderIntegrationRow(e,t))}
      </details>

      <details class="card" ?open=${this._isOpen("host-probe")} @toggle=${e=>this._onToggle("host-probe",e)}>
        <summary class="card-summary"><h3>Host Probe Add-on</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Real socket-level port visibility on the Home Assistant host needs the optional
          <strong>HA SOC Probe</strong> companion add-on — see the Scanner tab's Host
          Probe card for its current status, and the project README for install steps.
          The add-on's own scan interval is set from its add-on Configuration tab.
        </p>
      </details>

      <details class="card" ?open=${this._isOpen("snmpv3")} @toggle=${e=>this._onToggle("snmpv3",e)}>
        <summary class="card-summary"><h3>SNMPv3 Telemetry</h3>${this._statusPill(e,"snmpv3")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Optional read-only Net-SNMP service in the HA SOC Probe for monitoring and
          observability tools. Only SNMPv3 USM <strong>AuthPriv</strong> is supported,
          using SHA-256 authentication and AES-128 privacy. SNMPv1/v2c, write access,
          and wildcard listeners are not available.
        </p>
        <label class="settings-row">
          <span>
            Listener IP
            <span class="muted" style="display:block;font-size:11.5px;"
              >An exact Home Assistant address, such as 192.168.30.3; never 0.0.0.0.</span
            >
          </span>
          <input
            type="text"
            placeholder="e.g. 192.168.30.3"
            .value=${e.snmp_listen_address??""}
            @change=${e=>{const t=e.target.value.trim();this._update("snmp_listen_address",t||null)}}
          />
        </label>
        <label class="settings-row">
          <span>Port</span>
          <input
            type="number"
            min="1"
            max="65535"
            .value=${String(e.snmp_port)}
            @change=${e=>this._update("snmp_port",Number(e.target.value))}
          />
        </label>
        <label class="settings-row">
          <span>Security name</span>
          <input
            type="text"
            placeholder="e.g. solarwinds_sem"
            .value=${e.snmp_username??""}
            @change=${e=>{const t=e.target.value.trim();this._update("snmp_username",t||null)}}
          />
        </label>
        ${this._renderSecretField("Authentication passphrase (20+ characters)","snmp_auth_passphrase",!!e.snmp_auth_passphrase_set)}
        ${this._renderSecretField("Privacy passphrase (20+ characters, different)","snmp_priv_passphrase",!!e.snmp_priv_passphrase_set)}
        <p class="muted" style="font-size:11.5px;">
          Accepted credential characters: letters, numbers, and
          <code>._~!@$%^&amp;*+=:,-</code>. Restrict UDP/161 to your management or
          monitoring VLAN at the network firewall.
        </p>
        <label class="settings-row">
          <span>
            Enable SNMPv3
            <span class="muted" style="display:block;font-size:11.5px;"
              >The Probe must be installed and running. Complete every field above first.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${e.snmp_enabled}
            @change=${e=>this._update("snmp_enabled",e.target.checked)}
          />
        </label>
        ${e.snmp_status?K`<p class="muted" style="font-size:12px;">
              Probe status: ${e.snmp_status.error?`error — ${e.snmp_status.error}`:e.snmp_status.running?`running on ${e.snmp_status.listen_address}:${e.snmp_status.port}`:e.snmp_status.enabled?"enabled, waiting for snmpd":"disabled"}.
              ${e.snmp_status.reported_at?` Last report ${Si(e.snmp_status.reported_at)}.`:""}
            </p>`:K`<p class="muted" style="font-size:12px;">No SNMP status has been reported by the Probe yet.</p>`}
        ${e.snmp_status?.error?K`
              <div class="probe-error-notice">
                <div class="probe-error-text">${e.snmp_status.error}</div>
                <p class="probe-error-hint">
                  This usually means the Probe add-on hit a startup or permission problem.
                  Restarting the add-on re-runs its setup; if the error persists after a
                  restart, check the add-on's log (Settings → Add-ons → HA SOC Probe → Log)
                  for the full detail.
                </p>
                ${this._renderProbeRestart()}
              </div>
            `:""}
      </details>
      </div>
    `}};Ci.styles=qe,e([ue({attribute:!1})],Ci.prototype,"hass",void 0),e([pe()],Ci.prototype,"_settings",void 0),e([pe()],Ci.prototype,"_security",void 0),e([pe()],Ci.prototype,"_thresholds",void 0),e([pe()],Ci.prototype,"_loading",void 0),e([pe()],Ci.prototype,"_error",void 0),e([pe()],Ci.prototype,"_closedCards",void 0),e([pe()],Ci.prototype,"_connectionTests",void 0),e([pe()],Ci.prototype,"_probeRestart",void 0),e([pe()],Ci.prototype,"_discoverCandidates",void 0),Ci=e([he("ha-soc-settings-view")],Ci);
/**
 * Copyright (c) 2014-2024 The xterm.js authors. All rights reserved.
 * @license MIT
 *
 * Copyright (c) 2012-2013, Christopher Jeffrey (MIT License)
 * @license MIT
 *
 * Originally forked from (with the author's permission):
 *   Fabrice Bellard's javascript vt100 for jslinux:
 *   http://bellard.org/jslinux/
 *   Copyright (c) 2011 Fabrice Bellard
 */
var Ei=Object.defineProperty,Ri=Object.getOwnPropertyDescriptor,Pi=(e,t,s,i)=>{for(var r,n=i>1?void 0:i?Ri(t,s):t,o=e.length-1;o>=0;o--)(r=e[o])&&(n=(i?r(t,s,n):r(n))||n);return i&&n&&Ei(t,s,n),n},Ai=(e,t)=>(s,i)=>t(s,i,e),Ti="Terminal input",Di=()=>Ti,Li=e=>Ti=e,Mi="Too much output to announce, navigate to rows manually to read",Bi=()=>Mi,Oi=e=>Mi=e;function zi(e,t,s,i){e=function(e,t){return t?"[200~"+e+"[201~":e}(e=function(e){return e.replace(/\r?\n/g,"\r")}(e),s.decPrivateModes.bracketedPasteMode&&!0!==i.rawOptions.ignoreBracketedPasteMode),s.triggerDataEvent(e,!0),t.value=""}function Ii(e,t,s){let i=s.getBoundingClientRect(),r=e.clientX-i.left-10,n=e.clientY-i.top-10;t.style.width="20px",t.style.height="20px",t.style.left=`${r}px`,t.style.top=`${n}px`,t.style.zIndex="1000",t.focus()}function Ni(e,t,s,i,r){Ii(e,t,s),r&&i.rightClickSelect(e),t.value=i.selectionText,t.select()}function Fi(e){return e>65535?(e-=65536,String.fromCharCode(55296+(e>>10))+String.fromCharCode(e%1024+56320)):String.fromCharCode(e)}function Hi(e,t=0,s=e.length){let i="";for(let r=t;r<s;++r){let t=e[r];t>65535?(t-=65536,i+=String.fromCharCode(55296+(t>>10))+String.fromCharCode(t%1024+56320)):i+=String.fromCharCode(t)}return i}var Wi=class{constructor(){this._interim=0}clear(){this._interim=0}decode(e,t){let s=e.length;if(!s)return 0;let i=0,r=0;if(this._interim){let s=e.charCodeAt(r++);56320<=s&&s<=57343?t[i++]=1024*(this._interim-55296)+s-56320+65536:(t[i++]=this._interim,t[i++]=s),this._interim=0}for(let n=r;n<s;++n){let r=e.charCodeAt(n);if(55296<=r&&r<=56319){if(++n>=s)return this._interim=r,i;let o=e.charCodeAt(n);56320<=o&&o<=57343?t[i++]=1024*(r-55296)+o-56320+65536:(t[i++]=r,t[i++]=o);continue}65279!==r&&(t[i++]=r)}return i}},Ui=class{constructor(){this.interim=new Uint8Array(3)}clear(){this.interim.fill(0)}decode(e,t){let s=e.length;if(!s)return 0;let i,r,n,o,a=0,l=0,h=0;if(this.interim[0]){let i=!1,r=this.interim[0];r&=192==(224&r)?31:224==(240&r)?15:7;let n,o=0;for(;(n=63&this.interim[++o])&&o<4;)r<<=6,r|=n;let l=192==(224&this.interim[0])?2:224==(240&this.interim[0])?3:4,c=l-o;for(;h<c;){if(h>=s)return 0;if(n=e[h++],128!=(192&n)){h--,i=!0;break}this.interim[o++]=n,r<<=6,r|=63&n}i||(2===l?r<128?h--:t[a++]=r:3===l?r<2048||r>=55296&&r<=57343||65279===r||(t[a++]=r):r<65536||r>1114111||(t[a++]=r)),this.interim.fill(0)}let c=s-4,d=h;for(;d<s;){for(;!(!(d<c)||128&(i=e[d])||128&(r=e[d+1])||128&(n=e[d+2])||128&(o=e[d+3]));)t[a++]=i,t[a++]=r,t[a++]=n,t[a++]=o,d+=4;if(i=e[d++],i<128)t[a++]=i;else if(192==(224&i)){if(d>=s)return this.interim[0]=i,a;if(r=e[d++],128!=(192&r)){d--;continue}if(l=(31&i)<<6|63&r,l<128){d--;continue}t[a++]=l}else if(224==(240&i)){if(d>=s)return this.interim[0]=i,a;if(r=e[d++],128!=(192&r)){d--;continue}if(d>=s)return this.interim[0]=i,this.interim[1]=r,a;if(n=e[d++],128!=(192&n)){d--;continue}if(l=(15&i)<<12|(63&r)<<6|63&n,l<2048||l>=55296&&l<=57343||65279===l)continue;t[a++]=l}else if(240==(248&i)){if(d>=s)return this.interim[0]=i,a;if(r=e[d++],128!=(192&r)){d--;continue}if(d>=s)return this.interim[0]=i,this.interim[1]=r,a;if(n=e[d++],128!=(192&n)){d--;continue}if(d>=s)return this.interim[0]=i,this.interim[1]=r,this.interim[2]=n,a;if(o=e[d++],128!=(192&o)){d--;continue}if(l=(7&i)<<18|(63&r)<<12|(63&n)<<6|63&o,l<65536||l>1114111)continue;t[a++]=l}}return a}},Ki=" ",Vi=class e{constructor(){this.fg=0,this.bg=0,this.extended=new ji}static toColorRGB(e){return[e>>>16&255,e>>>8&255,255&e]}static fromColorRGB(e){return(255&e[0])<<16|(255&e[1])<<8|255&e[2]}clone(){let t=new e;return t.fg=this.fg,t.bg=this.bg,t.extended=this.extended.clone(),t}isInverse(){return 67108864&this.fg}isBold(){return 134217728&this.fg}isUnderline(){return this.hasExtendedAttrs()&&0!==this.extended.underlineStyle?1:268435456&this.fg}isBlink(){return 536870912&this.fg}isInvisible(){return 1073741824&this.fg}isItalic(){return 67108864&this.bg}isDim(){return 134217728&this.bg}isStrikethrough(){return 2147483648&this.fg}isProtected(){return 536870912&this.bg}isOverline(){return 1073741824&this.bg}getFgColorMode(){return 50331648&this.fg}getBgColorMode(){return 50331648&this.bg}isFgRGB(){return!(50331648&~this.fg)}isBgRGB(){return!(50331648&~this.bg)}isFgPalette(){return 16777216==(50331648&this.fg)||33554432==(50331648&this.fg)}isBgPalette(){return 16777216==(50331648&this.bg)||33554432==(50331648&this.bg)}isFgDefault(){return!(50331648&this.fg)}isBgDefault(){return!(50331648&this.bg)}isAttributeDefault(){return 0===this.fg&&0===this.bg}getFgColor(){switch(50331648&this.fg){case 16777216:case 33554432:return 255&this.fg;case 50331648:return 16777215&this.fg;default:return-1}}getBgColor(){switch(50331648&this.bg){case 16777216:case 33554432:return 255&this.bg;case 50331648:return 16777215&this.bg;default:return-1}}hasExtendedAttrs(){return 268435456&this.bg}updateExtended(){this.extended.isEmpty()?this.bg&=-268435457:this.bg|=268435456}getUnderlineColor(){if(268435456&this.bg&&~this.extended.underlineColor)switch(50331648&this.extended.underlineColor){case 16777216:case 33554432:return 255&this.extended.underlineColor;case 50331648:return 16777215&this.extended.underlineColor;default:return this.getFgColor()}return this.getFgColor()}getUnderlineColorMode(){return 268435456&this.bg&&~this.extended.underlineColor?50331648&this.extended.underlineColor:this.getFgColorMode()}isUnderlineColorRGB(){return 268435456&this.bg&&~this.extended.underlineColor?!(50331648&~this.extended.underlineColor):this.isFgRGB()}isUnderlineColorPalette(){return 268435456&this.bg&&~this.extended.underlineColor?16777216==(50331648&this.extended.underlineColor)||33554432==(50331648&this.extended.underlineColor):this.isFgPalette()}isUnderlineColorDefault(){return 268435456&this.bg&&~this.extended.underlineColor?!(50331648&this.extended.underlineColor):this.isFgDefault()}getUnderlineStyle(){return 268435456&this.fg?268435456&this.bg?this.extended.underlineStyle:1:0}getUnderlineVariantOffset(){return this.extended.underlineVariantOffset}},ji=class e{constructor(e=0,t=0){this._ext=0,this._urlId=0,this._ext=e,this._urlId=t}get ext(){return this._urlId?-469762049&this._ext|this.underlineStyle<<26:this._ext}set ext(e){this._ext=e}get underlineStyle(){return this._urlId?5:(469762048&this._ext)>>26}set underlineStyle(e){this._ext&=-469762049,this._ext|=e<<26&469762048}get underlineColor(){return 67108863&this._ext}set underlineColor(e){this._ext&=-67108864,this._ext|=67108863&e}get urlId(){return this._urlId}set urlId(e){this._urlId=e}get underlineVariantOffset(){let e=(3758096384&this._ext)>>29;return e<0?4294967288^e:e}set underlineVariantOffset(e){this._ext&=536870911,this._ext|=e<<29&3758096384}clone(){return new e(this._ext,this._urlId)}isEmpty(){return 0===this.underlineStyle&&0===this._urlId}},qi=class e extends Vi{constructor(){super(...arguments),this.content=0,this.fg=0,this.bg=0,this.extended=new ji,this.combinedData=""}static fromCharData(t){let s=new e;return s.setFromCharData(t),s}isCombined(){return 2097152&this.content}getWidth(){return this.content>>22}getChars(){return 2097152&this.content?this.combinedData:2097151&this.content?Fi(2097151&this.content):""}getCode(){return this.isCombined()?this.combinedData.charCodeAt(this.combinedData.length-1):2097151&this.content}setFromCharData(e){this.fg=e[0],this.bg=0;let t=!1;if(e[1].length>2)t=!0;else if(2===e[1].length){let s=e[1].charCodeAt(0);if(55296<=s&&s<=56319){let i=e[1].charCodeAt(1);56320<=i&&i<=57343?this.content=1024*(s-55296)+i-56320+65536|e[2]<<22:t=!0}else t=!0}else this.content=e[1].charCodeAt(0)|e[2]<<22;t&&(this.combinedData=e[1],this.content=2097152|e[2]<<22)}getAsCharData(){return[this.fg,this.getChars(),this.getWidth(),this.getCode()]}},Yi="di$target",Gi="di$dependencies",Xi=new Map;function Ji(e){if(Xi.has(e))return Xi.get(e);let t=function(e,s,i){if(3!==arguments.length)throw new Error("@IServiceName-decorator can only be used to decorate a parameter");!function(e,t,s){t[Yi]===t?t[Gi].push({id:e,index:s}):(t[Gi]=[{id:e,index:s}],t[Yi]=t)}(t,e,i)};return t._id=e,Xi.set(e,t),t}var Zi=Ji("BufferService"),Qi=Ji("CoreMouseService"),er=Ji("CoreService"),tr=Ji("CharsetService"),sr=Ji("InstantiationService"),ir=Ji("LogService"),rr=Ji("OptionsService"),nr=Ji("OscLinkService"),or=Ji("UnicodeService"),ar=Ji("DecorationService"),lr=class{constructor(e,t,s){this._bufferService=e,this._optionsService=t,this._oscLinkService=s}provideLinks(e,t){let s=this._bufferService.buffer.lines.get(e-1);if(!s)return void t(void 0);let i=[],r=this._optionsService.rawOptions.linkHandler,n=new qi,o=s.getTrimmedLength(),a=-1,l=-1,h=!1;for(let t=0;t<o;t++)if(-1!==l||s.hasContent(t)){if(s.loadCell(t,n),n.hasExtendedAttrs()&&n.extended.urlId){if(-1===l){l=t,a=n.extended.urlId;continue}h=n.extended.urlId!==a}else-1!==l&&(h=!0);if(h||-1!==l&&t===o-1){let s=this._oscLinkService.getLinkData(a)?.uri;if(s){let n={start:{x:l+1,y:e},end:{x:t+(h||t!==o-1?0:1),y:e}},a=!1;if(!r?.allowNonHttpProtocols)try{let e=new URL(s);["http:","https:"].includes(e.protocol)||(a=!0)}catch{a=!0}a||i.push({text:s,range:n,activate:(e,t)=>r?r.activate(e,t,n):hr(e,t),hover:(e,t)=>r?.hover?.(e,t,n),leave:(e,t)=>r?.leave?.(e,t,n)})}h=!1,n.hasExtendedAttrs()&&n.extended.urlId?(l=t,a=n.extended.urlId):(l=-1,a=-1)}}t(i)}};function hr(e,t){if(confirm(`Do you want to navigate to ${t}?\n\nWARNING: This link could potentially be dangerous`)){let e=window.open();if(e){try{e.opener=null}catch{}e.location.href=t}else console.warn("Opening link blocked as opener could not be cleared")}}lr=Pi([Ai(0,Zi),Ai(1,rr),Ai(2,nr)],lr);var cr=Ji("CharSizeService"),dr=Ji("CoreBrowserService"),ur=Ji("MouseService"),pr=Ji("RenderService"),_r=Ji("SelectionService"),fr=Ji("CharacterJoinerService"),gr=Ji("ThemeService"),vr=Ji("LinkProviderService"),mr=new class{constructor(){this.listeners=[],this.unexpectedErrorHandler=function(e){setTimeout(()=>{throw e.stack?$r.isErrorNoTelemetry(e)?new $r(e.message+"\n\n"+e.stack):new Error(e.message+"\n\n"+e.stack):e},0)}}addListener(e){return this.listeners.push(e),()=>{this._removeListener(e)}}emit(e){this.listeners.forEach(t=>{t(e)})}_removeListener(e){this.listeners.splice(this.listeners.indexOf(e),1)}setUnexpectedErrorHandler(e){this.unexpectedErrorHandler=e}getUnexpectedErrorHandler(){return this.unexpectedErrorHandler}onUnexpectedError(e){this.unexpectedErrorHandler(e),this.emit(e)}onUnexpectedExternalError(e){this.unexpectedErrorHandler(e)}};function yr(e){(function(e){return e instanceof wr||e instanceof Error&&e.name===br&&e.message===br})(e)||mr.onUnexpectedError(e)}var br="Canceled";var wr=class extends Error{constructor(){super(br),this.name=this.message}};var Sr,xr,$r=class e extends Error{constructor(e){super(e),this.name="CodeExpectedError"}static fromError(t){if(t instanceof e)return t;let s=new e;return s.message=t.message,s.stack=t.stack,s}static isErrorNoTelemetry(e){return"CodeExpectedError"===e.name}},kr=class e extends Error{constructor(t){super(t||"An unexpected bug occurred."),Object.setPrototypeOf(this,e.prototype)}};function Cr(e,t=0){return e[e.length-(1+t)]}function Er(e,t){let s,i=this,r=!1;return function(){return r||(r=!0,t||(s=e.apply(i,arguments))),s}}function Rr(e){if(xr.is(e)){let t=[];for(let s of e)if(s)try{s.dispose()}catch(e){t.push(e)}if(1===t.length)throw t[0];if(t.length>1)throw new AggregateError(t,"Encountered errors while disposing of store");return Array.isArray(e)?[]:e}if(e)return e.dispose(),e}function Pr(e){return{dispose:Er(()=>{e()})}}(e=>{e.isLessThan=function(e){return e<0},e.isLessThanOrEqual=function(e){return e<=0},e.isGreaterThan=function(e){return e>0},e.isNeitherLessOrGreaterThan=function(e){return 0===e},e.greaterThan=1,e.lessThan=-1,e.neitherLessOrGreaterThan=0})(Sr||={}),(e=>{function t(e){return e&&"object"==typeof e&&"function"==typeof e[Symbol.iterator]}e.is=t;let s=Object.freeze([]);function*i(e){yield e}e.empty=function(){return s},e.single=i,e.wrap=function(e){return t(e)?e:i(e)},e.from=function(e){return e||s},e.reverse=function*(e){for(let t=e.length-1;t>=0;t--)yield e[t]},e.isEmpty=function(e){return!e||!0===e[Symbol.iterator]().next().done},e.first=function(e){return e[Symbol.iterator]().next().value},e.some=function(e,t){let s=0;for(let i of e)if(t(i,s++))return!0;return!1},e.find=function(e,t){for(let s of e)if(t(s))return s},e.filter=function*(e,t){for(let s of e)t(s)&&(yield s)},e.map=function*(e,t){let s=0;for(let i of e)yield t(i,s++)},e.flatMap=function*(e,t){let s=0;for(let i of e)yield*t(i,s++)},e.concat=function*(...e){for(let t of e)yield*t},e.reduce=function(e,t,s){let i=s;for(let s of e)i=t(i,s);return i},e.slice=function*(e,t,s=e.length){for(t<0&&(t+=e.length),s<0?s+=e.length:s>e.length&&(s=e.length);t<s;t++)yield e[t]},e.consume=function(t,s=Number.POSITIVE_INFINITY){let i=[];if(0===s)return[i,t];let r=t[Symbol.iterator]();for(let t=0;t<s;t++){let t=r.next();if(t.done)return[i,e.empty()];i.push(t.value)}return[i,{[Symbol.iterator]:()=>r}]},e.asyncToArray=async function(e){let t=[];for await(let s of e)t.push(s);return Promise.resolve(t)}})(xr||={});var Ar=class e{constructor(){this._toDispose=new Set,this._isDisposed=!1}dispose(){this._isDisposed||(this._isDisposed=!0,this.clear())}get isDisposed(){return this._isDisposed}clear(){if(0!==this._toDispose.size)try{Rr(this._toDispose)}finally{this._toDispose.clear()}}add(t){if(!t)return t;if(t===this)throw new Error("Cannot register a disposable on itself!");return this._isDisposed?e.DISABLE_DISPOSED_WARNING||console.warn(new Error("Trying to add a disposable to a DisposableStore that has already been disposed of. The added object will be leaked!").stack):this._toDispose.add(t),t}delete(e){if(e){if(e===this)throw new Error("Cannot dispose a disposable on itself!");this._toDispose.delete(e),e.dispose()}}deleteAndLeak(e){e&&this._toDispose.has(e)&&this._toDispose.delete(e)}};Ar.DISABLE_DISPOSED_WARNING=!1;var Tr=Ar,Dr=class{constructor(){this._store=new Tr,this._store}dispose(){this._store.dispose()}_register(e){if(e===this)throw new Error("Cannot register a disposable on itself!");return this._store.add(e)}};Dr.None=Object.freeze({dispose(){}});var Lr=class{constructor(){this._isDisposed=!1}get value(){return this._isDisposed?void 0:this._value}set value(e){this._isDisposed||e===this._value||(this._value?.dispose(),this._value=e)}clear(){this.value=void 0}dispose(){this._isDisposed=!0,this._value?.dispose(),this._value=void 0}clearAndLeak(){let e=this._value;return this._value=void 0,e}},Mr="object"==typeof window?window:globalThis,Br=class e{constructor(t){this.element=t,this.next=e.Undefined,this.prev=e.Undefined}};Br.Undefined=new Br(void 0);var Or,zr=Br,Ir=class{constructor(){this._first=zr.Undefined,this._last=zr.Undefined,this._size=0}get size(){return this._size}isEmpty(){return this._first===zr.Undefined}clear(){let e=this._first;for(;e!==zr.Undefined;){let t=e.next;e.prev=zr.Undefined,e.next=zr.Undefined,e=t}this._first=zr.Undefined,this._last=zr.Undefined,this._size=0}unshift(e){return this._insert(e,!1)}push(e){return this._insert(e,!0)}_insert(e,t){let s=new zr(e);if(this._first===zr.Undefined)this._first=s,this._last=s;else if(t){let e=this._last;this._last=s,s.prev=e,e.next=s}else{let e=this._first;this._first=s,s.next=e,e.prev=s}this._size+=1;let i=!1;return()=>{i||(i=!0,this._remove(s))}}shift(){if(this._first!==zr.Undefined){let e=this._first.element;return this._remove(this._first),e}}pop(){if(this._last!==zr.Undefined){let e=this._last.element;return this._remove(this._last),e}}_remove(e){if(e.prev!==zr.Undefined&&e.next!==zr.Undefined){let t=e.prev;t.next=e.next,e.next.prev=t}else e.prev===zr.Undefined&&e.next===zr.Undefined?(this._first=zr.Undefined,this._last=zr.Undefined):e.next===zr.Undefined?(this._last=this._last.prev,this._last.next=zr.Undefined):e.prev===zr.Undefined&&(this._first=this._first.next,this._first.prev=zr.Undefined);this._size-=1}*[Symbol.iterator](){let e=this._first;for(;e!==zr.Undefined;)yield e.element,e=e.next}},Nr=globalThis.performance&&"function"==typeof globalThis.performance.now,Fr=class e{static create(t){return new e(t)}constructor(e){this._now=Nr&&!1===e?Date.now:globalThis.performance.now.bind(globalThis.performance),this._startTime=this._now(),this._stopTime=-1}stop(){this._stopTime=this._now()}reset(){this._startTime=this._now(),this._stopTime=-1}elapsed(){return-1!==this._stopTime?this._stopTime-this._startTime:this._now()-this._startTime}};(e=>{function t(e){return(t,s=null,i)=>{let r,n=!1;return r=e(e=>{if(!n)return r?r.dispose():n=!0,t.call(s,e)},null,i),n&&r.dispose(),r}}function s(e,t,s){return r((s,i=null,r)=>e(e=>s.call(i,t(e)),null,r),s)}function i(e,t,s){return r((s,i=null,r)=>e(e=>t(e)&&s.call(i,e),null,r),s)}function r(e,t){let s,i=new Xr({onWillAddFirstListener(){s=e(i.fire,i)},onDidRemoveLastListener(){s?.dispose()}});return t?.add(i),i.event}function n(e,t,s=100,i=!1,r=!1,n,o){let a,l,h,c,d=0,u=new Xr({leakWarningThreshold:n,onWillAddFirstListener(){a=e(e=>{d++,l=t(l,e),i&&!h&&(u.fire(l),l=void 0),c=()=>{let e=l;l=void 0,h=void 0,(!i||d>1)&&u.fire(e),d=0},"number"==typeof s?(clearTimeout(h),h=setTimeout(c,s)):void 0===h&&(h=0,queueMicrotask(c))})},onWillRemoveListener(){r&&d>0&&c?.()},onDidRemoveLastListener(){c=void 0,a.dispose()}});return o?.add(u),u.event}e.None=()=>Dr.None,e.defer=function(e,t){return n(e,()=>{},0,void 0,!0,void 0,t)},e.once=t,e.map=s,e.forEach=function(e,t,s){return r((s,i=null,r)=>e(e=>{t(e),s.call(i,e)},null,r),s)},e.filter=i,e.signal=function(e){return e},e.any=function(...e){return(t,s=null,i)=>{let r=function(...e){return Pr(()=>Rr(e))}(...e.map(e=>e(e=>t.call(s,e))));return function(e,t){return t instanceof Array?t.push(e):t&&t.add(e),e}(r,i)}},e.reduce=function(e,t,i,r){let n=i;return s(e,e=>(n=t(n,e),n),r)},e.debounce=n,e.accumulate=function(t,s=0,i){return e.debounce(t,(e,t)=>e?(e.push(t),e):[t],s,void 0,!0,void 0,i)},e.latch=function(e,t=(e,t)=>e===t,s){let r,n=!0;return i(e,e=>{let s=n||!t(e,r);return n=!1,r=e,s},s)},e.split=function(t,s,i){return[e.filter(t,s,i),e.filter(t,e=>!s(e),i)]},e.buffer=function(e,t=!1,s=[],i){let r=s.slice(),n=e(e=>{r?r.push(e):a.fire(e)});i&&i.add(n);let o=()=>{r?.forEach(e=>a.fire(e)),r=null},a=new Xr({onWillAddFirstListener(){n||(n=e(e=>a.fire(e)),i&&i.add(n))},onDidAddFirstListener(){r&&(t?setTimeout(o):o())},onDidRemoveLastListener(){n&&n.dispose(),n=null}});return i&&i.add(a),a.event},e.chain=function(e,t){return(s,i,r)=>{let n=t(new a);return e(function(e){let t=n.evaluate(e);t!==o&&s.call(i,t)},void 0,r)}};let o=Symbol("HaltChainable");class a{constructor(){this.steps=[]}map(e){return this.steps.push(e),this}forEach(e){return this.steps.push(t=>(e(t),t)),this}filter(e){return this.steps.push(t=>e(t)?t:o),this}reduce(e,t){let s=t;return this.steps.push(t=>(s=e(s,t),s)),this}latch(e=(e,t)=>e===t){let t,s=!0;return this.steps.push(i=>{let r=s||!e(i,t);return s=!1,t=i,r?i:o}),this}evaluate(e){for(let t of this.steps)if((e=t(e))===o)break;return e}}e.fromNodeEventEmitter=function(e,t,s=e=>e){let i=(...e)=>r.fire(s(...e)),r=new Xr({onWillAddFirstListener:()=>e.on(t,i),onDidRemoveLastListener:()=>e.removeListener(t,i)});return r.event},e.fromDOMEventEmitter=function(e,t,s=e=>e){let i=(...e)=>r.fire(s(...e)),r=new Xr({onWillAddFirstListener:()=>e.addEventListener(t,i),onDidRemoveLastListener:()=>e.removeEventListener(t,i)});return r.event},e.toPromise=function(e){return new Promise(s=>t(e)(s))},e.fromPromise=function(e){let t=new Xr;return e.then(e=>{t.fire(e)},()=>{t.fire(void 0)}).finally(()=>{t.dispose()}),t.event},e.forward=function(e,t){return e(e=>t.fire(e))},e.runAndSubscribe=function(e,t,s){return t(s),e(e=>t(e))};class l{constructor(e,t){this._observable=e,this._counter=0,this._hasChanged=!1;let s={onWillAddFirstListener:()=>{e.addObserver(this)},onDidRemoveLastListener:()=>{e.removeObserver(this)}};this.emitter=new Xr(s),t&&t.add(this.emitter)}beginUpdate(e){this._counter++}handlePossibleChange(e){}handleChange(e,t){this._hasChanged=!0}endUpdate(e){this._counter--,0===this._counter&&(this._observable.reportChanges(),this._hasChanged&&(this._hasChanged=!1,this.emitter.fire(this._observable.get())))}}e.fromObservable=function(e,t){return new l(e,t).emitter.event},e.fromObservableLight=function(e){return(t,s,i)=>{let r=0,n=!1,o={beginUpdate(){r++},endUpdate(){r--,0===r&&(e.reportChanges(),n&&(n=!1,t.call(s)))},handlePossibleChange(){},handleChange(){n=!0}};e.addObserver(o),e.reportChanges();let a={dispose(){e.removeObserver(o)}};return i instanceof Tr?i.add(a):Array.isArray(i)&&i.push(a),a}}})(Or||={});var Hr=class e{constructor(t){this.listenerCount=0,this.invocationCount=0,this.elapsedOverall=0,this.durations=[],this.name=`${t}_${e._idPool++}`,e.all.add(this)}start(e){this._stopWatch=new Fr,this.listenerCount=e}stop(){if(this._stopWatch){let e=this._stopWatch.elapsed();this.durations.push(e),this.elapsedOverall+=e,this.invocationCount+=1,this._stopWatch=void 0}}};Hr.all=new Set,Hr._idPool=0;var Wr=Hr,Ur=class e{constructor(t,s,i=(e._idPool++).toString(16).padStart(3,"0")){this._errorHandler=t,this.threshold=s,this.name=i,this._warnCountdown=0}dispose(){this._stacks?.clear()}check(e,t){let s=this.threshold;if(s<=0||t<s)return;this._stacks||(this._stacks=new Map);let i=this._stacks.get(e.value)||0;if(this._stacks.set(e.value,i+1),this._warnCountdown-=1,this._warnCountdown<=0){this._warnCountdown=.5*s;let[e,i]=this.getMostFrequentStack(),r=`[${this.name}] potential listener LEAK detected, having ${t} listeners already. MOST frequent listener (${i}):`;console.warn(r),console.warn(e);let n=new jr(r,e);this._errorHandler(n)}return()=>{let t=this._stacks.get(e.value)||0;this._stacks.set(e.value,t-1)}}getMostFrequentStack(){if(!this._stacks)return;let e,t=0;for(let[s,i]of this._stacks)(!e||t<i)&&(e=[s,i],t=i);return e}};Ur._idPool=1;var Kr=Ur,Vr=class e{constructor(e){this.value=e}static create(){let t=new Error;return new e(t.stack??"")}print(){console.warn(this.value.split("\n").slice(2).join("\n"))}},jr=class extends Error{constructor(e,t){super(e),this.name="ListenerLeakError",this.stack=t}},qr=class extends Error{constructor(e,t){super(e),this.name="ListenerRefusalError",this.stack=t}},Yr=0,Gr=class{constructor(e){this.value=e,this.id=Yr++}},Xr=class{constructor(e){this._size=0,this._options=e,this._leakageMon=this._options?.leakWarningThreshold?new Kr(e?.onListenerError??yr,this._options?.leakWarningThreshold??-1):void 0,this._perfMon=this._options?._profName?new Wr(this._options._profName):void 0,this._deliveryQueue=this._options?.deliveryQueue}dispose(){this._disposed||(this._disposed=!0,this._deliveryQueue?.current===this&&this._deliveryQueue.reset(),this._listeners&&(this._listeners=void 0,this._size=0),this._options?.onDidRemoveLastListener?.(),this._leakageMon?.dispose())}get event(){return this._event??=(e,t,s)=>{if(this._leakageMon&&this._size>this._leakageMon.threshold**2){let e=`[${this._leakageMon.name}] REFUSES to accept new listeners because it exceeded its threshold by far (${this._size} vs ${this._leakageMon.threshold})`;console.warn(e);let t=this._leakageMon.getMostFrequentStack()??["UNKNOWN stack",-1],s=new qr(`${e}. HINT: Stack shows most frequent listener (${t[1]}-times)`,t[0]);return(this._options?.onListenerError||yr)(s),Dr.None}if(this._disposed)return Dr.None;t&&(e=e.bind(t));let i,r=new Gr(e);this._leakageMon&&this._size>=Math.ceil(.2*this._leakageMon.threshold)&&(r.stack=Vr.create(),i=this._leakageMon.check(r.stack,this._size+1)),this._listeners?this._listeners instanceof Gr?(this._deliveryQueue??=new Jr,this._listeners=[this._listeners,r]):this._listeners.push(r):(this._options?.onWillAddFirstListener?.(this),this._listeners=r,this._options?.onDidAddFirstListener?.(this)),this._size++;let n=Pr(()=>{i?.(),this._removeListener(r)});return s instanceof Tr?s.add(n):Array.isArray(s)&&s.push(n),n},this._event}_removeListener(e){if(this._options?.onWillRemoveListener?.(this),!this._listeners)return;if(1===this._size)return this._listeners=void 0,this._options?.onDidRemoveLastListener?.(this),void(this._size=0);let t=this._listeners,s=t.indexOf(e);if(-1===s)throw console.log("disposed?",this._disposed),console.log("size?",this._size),console.log("arr?",JSON.stringify(this._listeners)),new Error("Attempted to dispose unknown listener");this._size--,t[s]=void 0;let i=this._deliveryQueue.current===this;if(2*this._size<=t.length){let e=0;for(let s=0;s<t.length;s++)t[s]?t[e++]=t[s]:i&&(this._deliveryQueue.end--,e<this._deliveryQueue.i&&this._deliveryQueue.i--);t.length=e}}_deliver(e,t){if(!e)return;let s=this._options?.onListenerError||yr;if(s)try{e.value(t)}catch(e){s(e)}else e.value(t)}_deliverQueue(e){let t=e.current._listeners;for(;e.i<e.end;)this._deliver(t[e.i++],e.value);e.reset()}fire(e){if(this._deliveryQueue?.current&&(this._deliverQueue(this._deliveryQueue),this._perfMon?.stop()),this._perfMon?.start(this._size),this._listeners)if(this._listeners instanceof Gr)this._deliver(this._listeners,e);else{let t=this._deliveryQueue;t.enqueue(this,e,this._listeners.length),this._deliverQueue(t)}this._perfMon?.stop()}hasListeners(){return this._size>0}},Jr=class{constructor(){this.i=-1,this.end=0}enqueue(e,t,s){this.i=0,this.end=s,this.current=e,this.value=t}reset(){this.i=this.end,this.current=void 0,this.value=void 0}},Zr=class{constructor(){this.mapWindowIdToZoomLevel=new Map,this._onDidChangeZoomLevel=new Xr,this.onDidChangeZoomLevel=this._onDidChangeZoomLevel.event,this.mapWindowIdToZoomFactor=new Map,this._onDidChangeFullscreen=new Xr,this.onDidChangeFullscreen=this._onDidChangeFullscreen.event,this.mapWindowIdToFullScreen=new Map}getZoomLevel(e){return this.mapWindowIdToZoomLevel.get(this.getWindowId(e))??0}setZoomLevel(e,t){if(this.getZoomLevel(t)===e)return;let s=this.getWindowId(t);this.mapWindowIdToZoomLevel.set(s,e),this._onDidChangeZoomLevel.fire(s)}getZoomFactor(e){return this.mapWindowIdToZoomFactor.get(this.getWindowId(e))??1}setZoomFactor(e,t){this.mapWindowIdToZoomFactor.set(this.getWindowId(t),e)}setFullscreen(e,t){if(this.isFullscreen(t)===e)return;let s=this.getWindowId(t);this.mapWindowIdToFullScreen.set(s,e),this._onDidChangeFullscreen.fire(s)}isFullscreen(e){return!!this.mapWindowIdToFullScreen.get(this.getWindowId(e))}getWindowId(e){return e.vscodeWindowId}};Zr.INSTANCE=new Zr;var Qr=Zr;Qr.INSTANCE.onDidChangeZoomLevel,Qr.INSTANCE.onDidChangeFullscreen;var en="object"==typeof navigator?navigator.userAgent:"",tn=en.indexOf("Firefox")>=0,sn=en.indexOf("AppleWebKit")>=0,rn=en.indexOf("Chrome")>=0,nn=!rn&&en.indexOf("Safari")>=0;en.indexOf("Electron/"),en.indexOf("Android");var on=!1;if("function"==typeof Mr.matchMedia){let e=Mr.matchMedia("(display-mode: standalone) or (display-mode: window-controls-overlay)"),t=Mr.matchMedia("(display-mode: fullscreen)");on=e.matches,function(e,t,s){"string"==typeof t&&(t=e.matchMedia(t)),t.addEventListener("change",s)}(Mr,e,({matches:e})=>{on&&t.matches||(on=e)})}var an,ln,hn="en",cn=!1,dn=!1,un=!1,pn=!1,_n=hn,fn=globalThis;typeof fn.vscode<"u"&&typeof fn.vscode.process<"u"?ln=fn.vscode.process:typeof process<"u"&&"string"==typeof process?.versions?.node&&(ln=process);var gn="string"==typeof ln?.versions?.electron&&"renderer"===ln?.type;if("object"==typeof ln){cn="win32"===ln.platform,dn="darwin"===ln.platform,(un="linux"===ln.platform)&&!!ln.env.SNAP&&ln.env.SNAP_REVISION,!!ln.env.CI||ln.env.BUILD_ARTIFACTSTAGINGDIRECTORY,_n=hn;let e=ln.env.VSCODE_NLS_CONFIG;if(e)try{let t=JSON.parse(e);t.userLocale,t.osLocale,_n=t.resolvedLanguage||hn,t.languagePack?.translationsConfigFile}catch{}pn=!0}else"object"!=typeof navigator||gn?console.error("Unable to resolve platform."):(cn=(an=navigator.userAgent).indexOf("Windows")>=0,dn=an.indexOf("Macintosh")>=0,(an.indexOf("Macintosh")>=0||an.indexOf("iPad")>=0||an.indexOf("iPhone")>=0)&&!!navigator.maxTouchPoints&&navigator.maxTouchPoints,un=an.indexOf("Linux")>=0,an?.indexOf("Mobi"),_n=globalThis._VSCODE_NLS_LANGUAGE||hn,navigator.language.toLowerCase());var vn,mn=cn,yn=dn,bn=un,wn=pn,Sn=an,xn=_n;(e=>{e.value=function(){return xn},e.isDefaultVariant=function(){return 2===xn.length?"en"===xn:xn.length>=3&&("e"===xn[0]&&"n"===xn[1]&&"-"===xn[2])},e.isDefault=function(){return"en"===xn}})(vn||={});var $n="function"==typeof fn.postMessage&&!fn.importScripts;(()=>{if($n){let e=[];fn.addEventListener("message",t=>{if(t.data&&t.data.vscodeScheduleAsyncWork)for(let s=0,i=e.length;s<i;s++){let i=e[s];if(i.id===t.data.vscodeScheduleAsyncWork)return e.splice(s,1),void i.callback()}});let t=0;return s=>{let i=++t;e.push({id:i,callback:s}),fn.postMessage({vscodeScheduleAsyncWork:i},"*")}}})();var kn=!!(Sn&&Sn.indexOf("Chrome")>=0);Sn&&Sn.indexOf("Firefox"),!kn&&Sn&&Sn.indexOf("Safari"),Sn&&Sn.indexOf("Edg/"),Sn&&Sn.indexOf("Android");var Cn="object"==typeof navigator?navigator:{};wn||document.queryCommandSupported&&document.queryCommandSupported("copy")||Cn&&Cn.clipboard&&Cn.clipboard.writeText,wn||Cn&&Cn.clipboard&&Cn.clipboard.readText;var En,Rn=class{constructor(){this._keyCodeToStr=[],this._strToKeyCode=Object.create(null)}define(e,t){this._keyCodeToStr[e]=t,this._strToKeyCode[t.toLowerCase()]=e}keyCodeToStr(e){return this._keyCodeToStr[e]}strToKeyCode(e){return this._strToKeyCode[e.toLowerCase()]||0}},Pn=new Rn,An=new Rn,Tn=new Rn,Dn=new Array(230);(e=>{e.toString=function(e){return Pn.keyCodeToStr(e)},e.fromString=function(e){return Pn.strToKeyCode(e)},e.toUserSettingsUS=function(e){return An.keyCodeToStr(e)},e.toUserSettingsGeneral=function(e){return Tn.keyCodeToStr(e)},e.fromUserSettings=function(e){return An.strToKeyCode(e)||Tn.strToKeyCode(e)},e.toElectronAccelerator=function(e){if(e>=98&&e<=113)return null;switch(e){case 16:return"Up";case 18:return"Down";case 15:return"Left";case 17:return"Right"}return Pn.keyCodeToStr(e)}})(En||={});var Ln=class e{constructor(e,t,s,i,r){this.ctrlKey=e,this.shiftKey=t,this.altKey=s,this.metaKey=i,this.keyCode=r}equals(t){return t instanceof e&&this.ctrlKey===t.ctrlKey&&this.shiftKey===t.shiftKey&&this.altKey===t.altKey&&this.metaKey===t.metaKey&&this.keyCode===t.keyCode}getHashCode(){return`K${this.ctrlKey?"1":"0"}${this.shiftKey?"1":"0"}${this.altKey?"1":"0"}${this.metaKey?"1":"0"}${this.keyCode}`}isModifierKey(){return 0===this.keyCode||5===this.keyCode||57===this.keyCode||6===this.keyCode||4===this.keyCode}toKeybinding(){return new Mn([this])}isDuplicateModifierCase(){return this.ctrlKey&&5===this.keyCode||this.shiftKey&&4===this.keyCode||this.altKey&&6===this.keyCode||this.metaKey&&57===this.keyCode}},Mn=class{constructor(e){if(0===e.length)throw function(e){return new Error(`Illegal argument: ${e}`)}("chords");this.chords=e}getHashCode(){let e="";for(let t=0,s=this.chords.length;t<s;t++)0!==t&&(e+=";"),e+=this.chords[t].getHashCode();return e}equals(e){if(null===e||this.chords.length!==e.chords.length)return!1;for(let t=0;t<this.chords.length;t++)if(!this.chords[t].equals(e.chords[t]))return!1;return!0}};var Bn=yn?256:2048,On=yn?2048:256,zn=class{constructor(e){this._standardKeyboardEventBrand=!0;let t=e;this.browserEvent=t,this.target=t.target,this.ctrlKey=t.ctrlKey,this.shiftKey=t.shiftKey,this.altKey=t.altKey,this.metaKey=t.metaKey,this.altGraphKey=t.getModifierState?.("AltGraph"),this.keyCode=function(e){if(e.charCode){let t=String.fromCharCode(e.charCode).toUpperCase();return En.fromString(t)}let t=e.keyCode;if(3===t)return 7;if(tn)switch(t){case 59:return 85;case 60:if(bn)return 97;break;case 61:return 86;case 107:return 109;case 109:return 111;case 173:return 88;case 224:if(yn)return 57}else if(sn){if(yn&&93===t)return 57;if(!yn&&92===t)return 57}return Dn[t]||0}(t),this.code=t.code,this.ctrlKey=this.ctrlKey||5===this.keyCode,this.altKey=this.altKey||6===this.keyCode,this.shiftKey=this.shiftKey||4===this.keyCode,this.metaKey=this.metaKey||57===this.keyCode,this._asKeybinding=this._computeKeybinding(),this._asKeyCodeChord=this._computeKeyCodeChord()}preventDefault(){this.browserEvent&&this.browserEvent.preventDefault&&this.browserEvent.preventDefault()}stopPropagation(){this.browserEvent&&this.browserEvent.stopPropagation&&this.browserEvent.stopPropagation()}toKeyCodeChord(){return this._asKeyCodeChord}equals(e){return this._asKeybinding===e}_computeKeybinding(){let e=0;5!==this.keyCode&&4!==this.keyCode&&6!==this.keyCode&&57!==this.keyCode&&(e=this.keyCode);let t=0;return this.ctrlKey&&(t|=Bn),this.altKey&&(t|=512),this.shiftKey&&(t|=1024),this.metaKey&&(t|=On),t|=e,t}_computeKeyCodeChord(){let e=0;return 5!==this.keyCode&&4!==this.keyCode&&6!==this.keyCode&&57!==this.keyCode&&(e=this.keyCode),new Ln(this.ctrlKey,this.shiftKey,this.altKey,this.metaKey,e)}},In=new WeakMap;function Nn(e){if(!e.parent||e.parent===e)return null;try{let t=e.location,s=e.parent.location;if("null"!==t.origin&&"null"!==s.origin&&t.origin!==s.origin)return null}catch{return null}return e.parent}var Fn,Hn=class{static getSameOriginWindowChain(e){let t=In.get(e);if(!t){t=[],In.set(e,t);let s,i=e;do{s=Nn(i),s?t.push({window:new WeakRef(i),iframeElement:i.frameElement||null}):t.push({window:new WeakRef(i),iframeElement:null}),i=s}while(i)}return t.slice(0)}static getPositionOfChildWindowRelativeToAncestorWindow(e,t){if(!t||e===t)return{top:0,left:0};let s=0,i=0,r=this.getSameOriginWindowChain(e);for(let e of r){let r=e.window.deref();if(s+=r?.scrollY??0,i+=r?.scrollX??0,r===t||!e.iframeElement)break;let n=e.iframeElement.getBoundingClientRect();s+=n.top,i+=n.left}return{top:s,left:i}}},Wn=class{constructor(e,t){this.timestamp=Date.now(),this.browserEvent=t,this.leftButton=0===t.button,this.middleButton=1===t.button,this.rightButton=2===t.button,this.buttons=t.buttons,this.target=t.target,this.detail=t.detail||1,"dblclick"===t.type&&(this.detail=2),this.ctrlKey=t.ctrlKey,this.shiftKey=t.shiftKey,this.altKey=t.altKey,this.metaKey=t.metaKey,"number"==typeof t.pageX?(this.posx=t.pageX,this.posy=t.pageY):(this.posx=t.clientX+this.target.ownerDocument.body.scrollLeft+this.target.ownerDocument.documentElement.scrollLeft,this.posy=t.clientY+this.target.ownerDocument.body.scrollTop+this.target.ownerDocument.documentElement.scrollTop);let s=Hn.getPositionOfChildWindowRelativeToAncestorWindow(e,t.view);this.posx-=s.left,this.posy-=s.top}preventDefault(){this.browserEvent.preventDefault()}stopPropagation(){this.browserEvent.stopPropagation()}},Un=class{constructor(e,t=0,s=0){this.browserEvent=e||null,this.target=e?e.target||e.targetNode||e.srcElement:null,this.deltaY=s,this.deltaX=t;let i=!1;if(rn){let e=navigator.userAgent.match(/Chrome\/(\d+)/);i=(e?parseInt(e[1]):123)<=122}if(e){let t=e,s=e,r=e.view?.devicePixelRatio||1;if(typeof t.wheelDeltaY<"u")this.deltaY=i?t.wheelDeltaY/(120*r):t.wheelDeltaY/120;else if(typeof s.VERTICAL_AXIS<"u"&&s.axis===s.VERTICAL_AXIS)this.deltaY=-s.detail/3;else if("wheel"===e.type){let t=e;t.deltaMode===t.DOM_DELTA_LINE?this.deltaY=tn&&!yn?-e.deltaY/3:-e.deltaY:this.deltaY=-e.deltaY/40}if(typeof t.wheelDeltaX<"u")this.deltaX=nn&&mn?-t.wheelDeltaX/120:i?t.wheelDeltaX/(120*r):t.wheelDeltaX/120;else if(typeof s.HORIZONTAL_AXIS<"u"&&s.axis===s.HORIZONTAL_AXIS)this.deltaX=-e.detail/3;else if("wheel"===e.type){let t=e;t.deltaMode===t.DOM_DELTA_LINE?this.deltaX=tn&&!yn?-e.deltaX/3:-e.deltaX:this.deltaX=-e.deltaX/40}0===this.deltaY&&0===this.deltaX&&e.wheelDelta&&(this.deltaY=i?e.wheelDelta/(120*r):e.wheelDelta/120)}}preventDefault(){this.browserEvent?.preventDefault()}stopPropagation(){this.browserEvent?.stopPropagation()}},Kn=Object.freeze(function(e,t){let s=setTimeout(e.bind(t),0);return{dispose(){clearTimeout(s)}}});(e=>{e.isCancellationToken=function(t){return t===e.None||t===e.Cancelled||t instanceof jn||!(!t||"object"!=typeof t)&&("boolean"==typeof t.isCancellationRequested&&"function"==typeof t.onCancellationRequested)},e.None=Object.freeze({isCancellationRequested:!1,onCancellationRequested:Or.None}),e.Cancelled=Object.freeze({isCancellationRequested:!0,onCancellationRequested:Kn})})(Fn||={});var Vn,jn=class{constructor(){this._isCancelled=!1,this._emitter=null}cancel(){this._isCancelled||(this._isCancelled=!0,this._emitter&&(this._emitter.fire(void 0),this.dispose()))}get isCancellationRequested(){return this._isCancelled}get onCancellationRequested(){return this._isCancelled?Kn:(this._emitter||(this._emitter=new Xr),this._emitter.event)}dispose(){this._emitter&&(this._emitter.dispose(),this._emitter=null)}},qn=class{constructor(e,t){this._isDisposed=!1,this._token=-1,"function"==typeof e&&"number"==typeof t&&this.setIfNotSet(e,t)}dispose(){this.cancel(),this._isDisposed=!0}cancel(){-1!==this._token&&(clearTimeout(this._token),this._token=-1)}cancelAndSet(e,t){if(this._isDisposed)throw new kr("Calling 'cancelAndSet' on a disposed TimeoutTimer");this.cancel(),this._token=setTimeout(()=>{this._token=-1,e()},t)}setIfNotSet(e,t){if(this._isDisposed)throw new kr("Calling 'setIfNotSet' on a disposed TimeoutTimer");-1===this._token&&(this._token=setTimeout(()=>{this._token=-1,e()},t))}},Yn=class{constructor(){this.disposable=void 0,this.isDisposed=!1}cancel(){this.disposable?.dispose(),this.disposable=void 0}cancelAndSet(e,t,s=globalThis){if(this.isDisposed)throw new kr("Calling 'cancelAndSet' on a disposed IntervalTimer");this.cancel();let i=s.setInterval(()=>{e()},t);this.disposable=Pr(()=>{s.clearInterval(i),this.disposable=void 0})}dispose(){this.cancel(),this.isDisposed=!0}};(e=>{e.settled=async function(e){let t,s=await Promise.all(e.map(e=>e.then(e=>e,e=>{t||(t=e)})));if(typeof t<"u")throw t;return s},e.withAsyncBody=function(e){return new Promise(async(t,s)=>{try{await e(t,s)}catch(e){s(e)}})}})(Vn||={});var Gn=class e{static fromArray(t){return new e(e=>{e.emitMany(t)})}static fromPromise(t){return new e(async e=>{e.emitMany(await t)})}static fromPromises(t){return new e(async e=>{await Promise.all(t.map(async t=>e.emitOne(await t)))})}static merge(t){return new e(async e=>{await Promise.all(t.map(async t=>{for await(let s of t)e.emitOne(s)}))})}constructor(e,t){this._state=0,this._results=[],this._error=null,this._onReturn=t,this._onStateChanged=new Xr,queueMicrotask(async()=>{let t={emitOne:e=>this.emitOne(e),emitMany:e=>this.emitMany(e),reject:e=>this.reject(e)};try{await Promise.resolve(e(t)),this.resolve()}catch(e){this.reject(e)}finally{t.emitOne=void 0,t.emitMany=void 0,t.reject=void 0}})}[Symbol.asyncIterator](){let e=0;return{next:async()=>{for(;;){if(2===this._state)throw this._error;if(e<this._results.length)return{done:!1,value:this._results[e++]};if(1===this._state)return{done:!0,value:void 0};await Or.toPromise(this._onStateChanged.event)}},return:async()=>(this._onReturn?.(),{done:!0,value:void 0})}}static map(t,s){return new e(async e=>{for await(let i of t)e.emitOne(s(i))})}map(t){return e.map(this,t)}static filter(t,s){return new e(async e=>{for await(let i of t)s(i)&&e.emitOne(i)})}filter(t){return e.filter(this,t)}static coalesce(t){return e.filter(t,e=>!!e)}coalesce(){return e.coalesce(this)}static async toPromise(e){let t=[];for await(let s of e)t.push(s);return t}toPromise(){return e.toPromise(this)}emitOne(e){0===this._state&&(this._results.push(e),this._onStateChanged.fire())}emitMany(e){0===this._state&&(this._results=this._results.concat(e),this._onStateChanged.fire())}resolve(){0===this._state&&(this._state=1,this._onStateChanged.fire())}reject(e){0===this._state&&(this._state=2,this._error=e,this._onStateChanged.fire())}};Gn.EMPTY=Gn.fromArray([]);var{getWindow:Xn,getWindowId:Jn,onDidRegisterWindow:Zn}=function(){let e=new Map,t={window:Mr,disposables:new Tr};e.set(Mr.vscodeWindowId,t);let s=new Xr,i=new Xr,r=new Xr;return{onDidRegisterWindow:s.event,onWillUnregisterWindow:r.event,onDidUnregisterWindow:i.event,registerWindow(t){if(e.has(t.vscodeWindowId))return Dr.None;let n=new Tr,o={window:t,disposables:n.add(new Tr)};return e.set(t.vscodeWindowId,o),n.add(Pr(()=>{e.delete(t.vscodeWindowId),i.fire(t)})),n.add(eo(t,no.BEFORE_UNLOAD,()=>{r.fire(t)})),s.fire(o),n},getWindows:()=>e.values(),getWindowsCount:()=>e.size,getWindowId:e=>e.vscodeWindowId,hasWindow:t=>e.has(t),getWindowById:function(s,i){return("number"==typeof s?e.get(s):void 0)??(i?t:void 0)},getWindow(e){let t=e;if(t?.ownerDocument?.defaultView)return t.ownerDocument.defaultView.window;let s=e;return s?.view?s.view.window:Mr},getDocument:e=>Xn(e).document}}(),Qn=class{constructor(e,t,s,i){this._node=e,this._type=t,this._handler=s,this._options=i||!1,this._node.addEventListener(this._type,this._handler,this._options)}dispose(){this._handler&&(this._node.removeEventListener(this._type,this._handler,this._options),this._node=null,this._handler=null)}};function eo(e,t,s,i){return new Qn(e,t,s,i)}var to,so=function(e,t,s,i){return eo(e,t,s,i)},io=class extends Yn{constructor(e){super(),this.defaultTarget=e&&Xn(e)}cancelAndSet(e,t,s){return super.cancelAndSet(e,t,s??this.defaultTarget)}},ro=class{constructor(e,t=0){this._runner=e,this.priority=t,this._canceled=!1}dispose(){this._canceled=!0}execute(){if(!this._canceled)try{this._runner()}catch(e){yr(e)}}static sort(e,t){return t.priority-e.priority}};!function(){let e=new Map,t=new Map,s=new Map,i=new Map;to=(r,n,o=0)=>{let a=Jn(r),l=new ro(n,o),h=e.get(a);return h||(h=[],e.set(a,h)),h.push(l),s.get(a)||(s.set(a,!0),r.requestAnimationFrame(()=>(r=>{s.set(r,!1);let n=e.get(r)??[];for(t.set(r,n),e.set(r,[]),i.set(r,!0);n.length>0;)n.sort(ro.sort),n.shift().execute();i.set(r,!1)})(a))),l}}();var no={CLICK:"click",MOUSE_DOWN:"mousedown",MOUSE_OVER:"mouseover",MOUSE_LEAVE:"mouseleave",MOUSE_WHEEL:"wheel",POINTER_UP:"pointerup",POINTER_DOWN:"pointerdown",POINTER_MOVE:"pointermove",KEY_DOWN:"keydown",KEY_UP:"keyup",BEFORE_UNLOAD:"beforeunload",CHANGE:"change",FOCUS:"focus",BLUR:"blur",INPUT:"input"},oo=class{constructor(e){this.domNode=e,this._maxWidth="",this._width="",this._height="",this._top="",this._left="",this._bottom="",this._right="",this._paddingTop="",this._paddingLeft="",this._paddingBottom="",this._paddingRight="",this._fontFamily="",this._fontWeight="",this._fontSize="",this._fontStyle="",this._fontFeatureSettings="",this._fontVariationSettings="",this._textDecoration="",this._lineHeight="",this._letterSpacing="",this._className="",this._display="",this._position="",this._visibility="",this._color="",this._backgroundColor="",this._layerHint=!1,this._contain="none",this._boxShadow=""}setMaxWidth(e){let t=ao(e);this._maxWidth!==t&&(this._maxWidth=t,this.domNode.style.maxWidth=this._maxWidth)}setWidth(e){let t=ao(e);this._width!==t&&(this._width=t,this.domNode.style.width=this._width)}setHeight(e){let t=ao(e);this._height!==t&&(this._height=t,this.domNode.style.height=this._height)}setTop(e){let t=ao(e);this._top!==t&&(this._top=t,this.domNode.style.top=this._top)}setLeft(e){let t=ao(e);this._left!==t&&(this._left=t,this.domNode.style.left=this._left)}setBottom(e){let t=ao(e);this._bottom!==t&&(this._bottom=t,this.domNode.style.bottom=this._bottom)}setRight(e){let t=ao(e);this._right!==t&&(this._right=t,this.domNode.style.right=this._right)}setPaddingTop(e){let t=ao(e);this._paddingTop!==t&&(this._paddingTop=t,this.domNode.style.paddingTop=this._paddingTop)}setPaddingLeft(e){let t=ao(e);this._paddingLeft!==t&&(this._paddingLeft=t,this.domNode.style.paddingLeft=this._paddingLeft)}setPaddingBottom(e){let t=ao(e);this._paddingBottom!==t&&(this._paddingBottom=t,this.domNode.style.paddingBottom=this._paddingBottom)}setPaddingRight(e){let t=ao(e);this._paddingRight!==t&&(this._paddingRight=t,this.domNode.style.paddingRight=this._paddingRight)}setFontFamily(e){this._fontFamily!==e&&(this._fontFamily=e,this.domNode.style.fontFamily=this._fontFamily)}setFontWeight(e){this._fontWeight!==e&&(this._fontWeight=e,this.domNode.style.fontWeight=this._fontWeight)}setFontSize(e){let t=ao(e);this._fontSize!==t&&(this._fontSize=t,this.domNode.style.fontSize=this._fontSize)}setFontStyle(e){this._fontStyle!==e&&(this._fontStyle=e,this.domNode.style.fontStyle=this._fontStyle)}setFontFeatureSettings(e){this._fontFeatureSettings!==e&&(this._fontFeatureSettings=e,this.domNode.style.fontFeatureSettings=this._fontFeatureSettings)}setFontVariationSettings(e){this._fontVariationSettings!==e&&(this._fontVariationSettings=e,this.domNode.style.fontVariationSettings=this._fontVariationSettings)}setTextDecoration(e){this._textDecoration!==e&&(this._textDecoration=e,this.domNode.style.textDecoration=this._textDecoration)}setLineHeight(e){let t=ao(e);this._lineHeight!==t&&(this._lineHeight=t,this.domNode.style.lineHeight=this._lineHeight)}setLetterSpacing(e){let t=ao(e);this._letterSpacing!==t&&(this._letterSpacing=t,this.domNode.style.letterSpacing=this._letterSpacing)}setClassName(e){this._className!==e&&(this._className=e,this.domNode.className=this._className)}toggleClassName(e,t){this.domNode.classList.toggle(e,t),this._className=this.domNode.className}setDisplay(e){this._display!==e&&(this._display=e,this.domNode.style.display=this._display)}setPosition(e){this._position!==e&&(this._position=e,this.domNode.style.position=this._position)}setVisibility(e){this._visibility!==e&&(this._visibility=e,this.domNode.style.visibility=this._visibility)}setColor(e){this._color!==e&&(this._color=e,this.domNode.style.color=this._color)}setBackgroundColor(e){this._backgroundColor!==e&&(this._backgroundColor=e,this.domNode.style.backgroundColor=this._backgroundColor)}setLayerHinting(e){this._layerHint!==e&&(this._layerHint=e,this.domNode.style.transform=this._layerHint?"translate3d(0px, 0px, 0px)":"")}setBoxShadow(e){this._boxShadow!==e&&(this._boxShadow=e,this.domNode.style.boxShadow=e)}setContain(e){this._contain!==e&&(this._contain=e,this.domNode.style.contain=this._contain)}setAttribute(e,t){this.domNode.setAttribute(e,t)}removeAttribute(e){this.domNode.removeAttribute(e)}appendChild(e){this.domNode.appendChild(e.domNode)}removeChild(e){this.domNode.removeChild(e.domNode)}};function ao(e){return"number"==typeof e?`${e}px`:e}function lo(e){return new oo(e)}var ho,co=class{constructor(){this._hooks=new Tr,this._pointerMoveCallback=null,this._onStopCallback=null}dispose(){this.stopMonitoring(!1),this._hooks.dispose()}stopMonitoring(e,t){if(!this.isMonitoring())return;this._hooks.clear(),this._pointerMoveCallback=null;let s=this._onStopCallback;this._onStopCallback=null,e&&s&&s(t)}isMonitoring(){return!!this._pointerMoveCallback}startMonitoring(e,t,s,i,r){this.isMonitoring()&&this.stopMonitoring(!1),this._pointerMoveCallback=i,this._onStopCallback=r;let n=e;try{e.setPointerCapture(t),this._hooks.add(Pr(()=>{try{e.releasePointerCapture(t)}catch{}}))}catch{n=Xn(e)}this._hooks.add(eo(n,no.POINTER_MOVE,e=>{e.buttons===s?(e.preventDefault(),this._pointerMoveCallback(e)):this.stopMonitoring(!0)})),this._hooks.add(eo(n,no.POINTER_UP,e=>this.stopMonitoring(!0)))}};(e=>{e.Tap="-xterm-gesturetap",e.Change="-xterm-gesturechange",e.Start="-xterm-gesturestart",e.End="-xterm-gesturesend",e.Contextmenu="-xterm-gesturecontextmenu"})(ho||={});var uo=class e extends Dr{constructor(){super(),this.dispatched=!1,this.targets=new Ir,this.ignoreTargets=new Ir,this.activeTouches={},this.handle=null,this._lastSetTapCountTime=0,this._register(Or.runAndSubscribe(Zn,({window:e,disposables:t})=>{t.add(eo(e.document,"touchstart",e=>this.onTouchStart(e),{passive:!1})),t.add(eo(e.document,"touchend",t=>this.onTouchEnd(e,t))),t.add(eo(e.document,"touchmove",e=>this.onTouchMove(e),{passive:!1}))},{window:Mr,disposables:this._store}))}static addTarget(t){if(!e.isTouchDevice())return Dr.None;return e.INSTANCE||(e.INSTANCE=new e),Pr(e.INSTANCE.targets.push(t))}static ignoreTarget(t){if(!e.isTouchDevice())return Dr.None;return e.INSTANCE||(e.INSTANCE=new e),Pr(e.INSTANCE.ignoreTargets.push(t))}static isTouchDevice(){return"ontouchstart"in Mr||navigator.maxTouchPoints>0}dispose(){this.handle&&(this.handle.dispose(),this.handle=null),super.dispose()}onTouchStart(e){let t=Date.now();this.handle&&(this.handle.dispose(),this.handle=null);for(let s=0,i=e.targetTouches.length;s<i;s++){let i=e.targetTouches.item(s);this.activeTouches[i.identifier]={id:i.identifier,initialTarget:i.target,initialTimeStamp:t,initialPageX:i.pageX,initialPageY:i.pageY,rollingTimestamps:[t],rollingPageX:[i.pageX],rollingPageY:[i.pageY]};let r=this.newGestureEvent(ho.Start,i.target);r.pageX=i.pageX,r.pageY=i.pageY,this.dispatchEvent(r)}this.dispatched&&(e.preventDefault(),e.stopPropagation(),this.dispatched=!1)}onTouchEnd(t,s){let i=Date.now(),r=Object.keys(this.activeTouches).length;for(let n=0,o=s.changedTouches.length;n<o;n++){let o=s.changedTouches.item(n);if(!this.activeTouches.hasOwnProperty(String(o.identifier))){console.warn("move of an UNKNOWN touch",o);continue}let a=this.activeTouches[o.identifier],l=Date.now()-a.initialTimeStamp;if(l<e.HOLD_DELAY&&Math.abs(a.initialPageX-Cr(a.rollingPageX))<30&&Math.abs(a.initialPageY-Cr(a.rollingPageY))<30){let e=this.newGestureEvent(ho.Tap,a.initialTarget);e.pageX=Cr(a.rollingPageX),e.pageY=Cr(a.rollingPageY),this.dispatchEvent(e)}else if(l>=e.HOLD_DELAY&&Math.abs(a.initialPageX-Cr(a.rollingPageX))<30&&Math.abs(a.initialPageY-Cr(a.rollingPageY))<30){let e=this.newGestureEvent(ho.Contextmenu,a.initialTarget);e.pageX=Cr(a.rollingPageX),e.pageY=Cr(a.rollingPageY),this.dispatchEvent(e)}else if(1===r){let e=Cr(a.rollingPageX),s=Cr(a.rollingPageY),r=Cr(a.rollingTimestamps)-a.rollingTimestamps[0],n=e-a.rollingPageX[0],o=s-a.rollingPageY[0],l=[...this.targets].filter(e=>a.initialTarget instanceof Node&&e.contains(a.initialTarget));this.inertia(t,l,i,Math.abs(n)/r,n>0?1:-1,e,Math.abs(o)/r,o>0?1:-1,s)}this.dispatchEvent(this.newGestureEvent(ho.End,a.initialTarget)),delete this.activeTouches[o.identifier]}this.dispatched&&(s.preventDefault(),s.stopPropagation(),this.dispatched=!1)}newGestureEvent(e,t){let s=document.createEvent("CustomEvent");return s.initEvent(e,!1,!0),s.initialTarget=t,s.tapCount=0,s}dispatchEvent(t){if(t.type===ho.Tap){let s=(new Date).getTime(),i=0;i=s-this._lastSetTapCountTime>e.CLEAR_TAP_COUNT_TIME?1:2,this._lastSetTapCountTime=s,t.tapCount=i}else(t.type===ho.Change||t.type===ho.Contextmenu)&&(this._lastSetTapCountTime=0);if(t.initialTarget instanceof Node){for(let e of this.ignoreTargets)if(e.contains(t.initialTarget))return;let e=[];for(let s of this.targets)if(s.contains(t.initialTarget)){let i=0,r=t.initialTarget;for(;r&&r!==s;)i++,r=r.parentElement;e.push([i,s])}e.sort((e,t)=>e[0]-t[0]);for(let[s,i]of e)i.dispatchEvent(t),this.dispatched=!0}}inertia(t,s,i,r,n,o,a,l,h){this.handle=to(t,()=>{let c=Date.now(),d=c-i,u=0,p=0,_=!0;r+=e.SCROLL_FRICTION*d,a+=e.SCROLL_FRICTION*d,r>0&&(_=!1,u=n*r*d),a>0&&(_=!1,p=l*a*d);let f=this.newGestureEvent(ho.Change);f.translationX=u,f.translationY=p,s.forEach(e=>e.dispatchEvent(f)),_||this.inertia(t,s,c,r,n,o+u,a,l,h+p)})}onTouchMove(e){let t=Date.now();for(let s=0,i=e.changedTouches.length;s<i;s++){let i=e.changedTouches.item(s);if(!this.activeTouches.hasOwnProperty(String(i.identifier))){console.warn("end of an UNKNOWN touch",i);continue}let r=this.activeTouches[i.identifier],n=this.newGestureEvent(ho.Change,r.initialTarget);n.translationX=i.pageX-Cr(r.rollingPageX),n.translationY=i.pageY-Cr(r.rollingPageY),n.pageX=i.pageX,n.pageY=i.pageY,this.dispatchEvent(n),r.rollingPageX.length>3&&(r.rollingPageX.shift(),r.rollingPageY.shift(),r.rollingTimestamps.shift()),r.rollingPageX.push(i.pageX),r.rollingPageY.push(i.pageY),r.rollingTimestamps.push(t)}this.dispatched&&(e.preventDefault(),e.stopPropagation(),this.dispatched=!1)}};uo.SCROLL_FRICTION=-.005,uo.HOLD_DELAY=700,uo.CLEAR_TAP_COUNT_TIME=400,Pi([function(e,t,s){let i=null,r=null;if("function"==typeof s.value?(i="value",r=s.value,0!==r.length&&console.warn("Memoize should only be used in functions with zero parameters")):"function"==typeof s.get&&(i="get",r=s.get),!r)throw new Error("not supported");let n=`$memoize$${t}`;s[i]=function(...e){return this.hasOwnProperty(n)||Object.defineProperty(this,n,{configurable:!1,enumerable:!1,writable:!1,value:r.apply(this,e)}),this[n]}}],uo,"isTouchDevice",1);var po=uo,_o=class extends Dr{onclick(e,t){this._register(eo(e,no.CLICK,s=>t(new Wn(Xn(e),s))))}onmousedown(e,t){this._register(eo(e,no.MOUSE_DOWN,s=>t(new Wn(Xn(e),s))))}onmouseover(e,t){this._register(eo(e,no.MOUSE_OVER,s=>t(new Wn(Xn(e),s))))}onmouseleave(e,t){this._register(eo(e,no.MOUSE_LEAVE,s=>t(new Wn(Xn(e),s))))}onkeydown(e,t){this._register(eo(e,no.KEY_DOWN,e=>t(new zn(e))))}onkeyup(e,t){this._register(eo(e,no.KEY_UP,e=>t(new zn(e))))}oninput(e,t){this._register(eo(e,no.INPUT,t))}onblur(e,t){this._register(eo(e,no.BLUR,t))}onfocus(e,t){this._register(eo(e,no.FOCUS,t))}onchange(e,t){this._register(eo(e,no.CHANGE,t))}ignoreGesture(e){return po.ignoreTarget(e)}},fo=class extends _o{constructor(e){super(),this._onActivate=e.onActivate,this.bgDomNode=document.createElement("div"),this.bgDomNode.className="arrow-background",this.bgDomNode.style.position="absolute",this.bgDomNode.style.width=e.bgWidth+"px",this.bgDomNode.style.height=e.bgHeight+"px",typeof e.top<"u"&&(this.bgDomNode.style.top="0px"),typeof e.left<"u"&&(this.bgDomNode.style.left="0px"),typeof e.bottom<"u"&&(this.bgDomNode.style.bottom="0px"),typeof e.right<"u"&&(this.bgDomNode.style.right="0px"),this.domNode=document.createElement("div"),this.domNode.className=e.className,this.domNode.style.position="absolute",this.domNode.style.width="11px",this.domNode.style.height="11px",typeof e.top<"u"&&(this.domNode.style.top=e.top+"px"),typeof e.left<"u"&&(this.domNode.style.left=e.left+"px"),typeof e.bottom<"u"&&(this.domNode.style.bottom=e.bottom+"px"),typeof e.right<"u"&&(this.domNode.style.right=e.right+"px"),this._pointerMoveMonitor=this._register(new co),this._register(so(this.bgDomNode,no.POINTER_DOWN,e=>this._arrowPointerDown(e))),this._register(so(this.domNode,no.POINTER_DOWN,e=>this._arrowPointerDown(e))),this._pointerdownRepeatTimer=this._register(new io),this._pointerdownScheduleRepeatTimer=this._register(new qn)}_arrowPointerDown(e){if(!(e.target&&e.target instanceof Element))return;this._onActivate(),this._pointerdownRepeatTimer.cancel(),this._pointerdownScheduleRepeatTimer.cancelAndSet(()=>{this._pointerdownRepeatTimer.cancelAndSet(()=>this._onActivate(),1e3/24,Xn(e))},200),this._pointerMoveMonitor.startMonitoring(e.target,e.pointerId,e.buttons,e=>{},()=>{this._pointerdownRepeatTimer.cancel(),this._pointerdownScheduleRepeatTimer.cancel()}),e.preventDefault()}},go=class e{constructor(e,t,s,i,r,n,o){this._forceIntegerValues=e,this._scrollStateBrand=void 0,this._forceIntegerValues&&(t|=0,s|=0,i|=0,r|=0,n|=0,o|=0),this.rawScrollLeft=i,this.rawScrollTop=o,t<0&&(t=0),i+t>s&&(i=s-t),i<0&&(i=0),r<0&&(r=0),o+r>n&&(o=n-r),o<0&&(o=0),this.width=t,this.scrollWidth=s,this.scrollLeft=i,this.height=r,this.scrollHeight=n,this.scrollTop=o}equals(e){return this.rawScrollLeft===e.rawScrollLeft&&this.rawScrollTop===e.rawScrollTop&&this.width===e.width&&this.scrollWidth===e.scrollWidth&&this.scrollLeft===e.scrollLeft&&this.height===e.height&&this.scrollHeight===e.scrollHeight&&this.scrollTop===e.scrollTop}withScrollDimensions(t,s){return new e(this._forceIntegerValues,typeof t.width<"u"?t.width:this.width,typeof t.scrollWidth<"u"?t.scrollWidth:this.scrollWidth,s?this.rawScrollLeft:this.scrollLeft,typeof t.height<"u"?t.height:this.height,typeof t.scrollHeight<"u"?t.scrollHeight:this.scrollHeight,s?this.rawScrollTop:this.scrollTop)}withScrollPosition(t){return new e(this._forceIntegerValues,this.width,this.scrollWidth,typeof t.scrollLeft<"u"?t.scrollLeft:this.rawScrollLeft,this.height,this.scrollHeight,typeof t.scrollTop<"u"?t.scrollTop:this.rawScrollTop)}createScrollEvent(e,t){let s=this.width!==e.width,i=this.scrollWidth!==e.scrollWidth,r=this.scrollLeft!==e.scrollLeft,n=this.height!==e.height,o=this.scrollHeight!==e.scrollHeight,a=this.scrollTop!==e.scrollTop;return{inSmoothScrolling:t,oldWidth:e.width,oldScrollWidth:e.scrollWidth,oldScrollLeft:e.scrollLeft,width:this.width,scrollWidth:this.scrollWidth,scrollLeft:this.scrollLeft,oldHeight:e.height,oldScrollHeight:e.scrollHeight,oldScrollTop:e.scrollTop,height:this.height,scrollHeight:this.scrollHeight,scrollTop:this.scrollTop,widthChanged:s,scrollWidthChanged:i,scrollLeftChanged:r,heightChanged:n,scrollHeightChanged:o,scrollTopChanged:a}}},vo=class extends Dr{constructor(e){super(),this._scrollableBrand=void 0,this._onScroll=this._register(new Xr),this.onScroll=this._onScroll.event,this._smoothScrollDuration=e.smoothScrollDuration,this._scheduleAtNextAnimationFrame=e.scheduleAtNextAnimationFrame,this._state=new go(e.forceIntegerValues,0,0,0,0,0,0),this._smoothScrolling=null}dispose(){this._smoothScrolling&&(this._smoothScrolling.dispose(),this._smoothScrolling=null),super.dispose()}setSmoothScrollDuration(e){this._smoothScrollDuration=e}validateScrollPosition(e){return this._state.withScrollPosition(e)}getScrollDimensions(){return this._state}setScrollDimensions(e,t){let s=this._state.withScrollDimensions(e,t);this._setState(s,!!this._smoothScrolling),this._smoothScrolling?.acceptScrollDimensions(this._state)}getFutureScrollPosition(){return this._smoothScrolling?this._smoothScrolling.to:this._state}getCurrentScrollPosition(){return this._state}setScrollPositionNow(e){let t=this._state.withScrollPosition(e);this._smoothScrolling&&(this._smoothScrolling.dispose(),this._smoothScrolling=null),this._setState(t,!1)}setScrollPositionSmooth(e,t){if(0===this._smoothScrollDuration)return this.setScrollPositionNow(e);if(this._smoothScrolling){e={scrollLeft:typeof e.scrollLeft>"u"?this._smoothScrolling.to.scrollLeft:e.scrollLeft,scrollTop:typeof e.scrollTop>"u"?this._smoothScrolling.to.scrollTop:e.scrollTop};let s,i=this._state.withScrollPosition(e);if(this._smoothScrolling.to.scrollLeft===i.scrollLeft&&this._smoothScrolling.to.scrollTop===i.scrollTop)return;s=t?new bo(this._smoothScrolling.from,i,this._smoothScrolling.startTime,this._smoothScrolling.duration):this._smoothScrolling.combine(this._state,i,this._smoothScrollDuration),this._smoothScrolling.dispose(),this._smoothScrolling=s}else{let t=this._state.withScrollPosition(e);this._smoothScrolling=bo.start(this._state,t,this._smoothScrollDuration)}this._smoothScrolling.animationFrameDisposable=this._scheduleAtNextAnimationFrame(()=>{this._smoothScrolling&&(this._smoothScrolling.animationFrameDisposable=null,this._performSmoothScrolling())})}hasPendingScrollAnimation(){return!!this._smoothScrolling}_performSmoothScrolling(){if(!this._smoothScrolling)return;let e=this._smoothScrolling.tick(),t=this._state.withScrollPosition(e);if(this._setState(t,!0),this._smoothScrolling){if(e.isDone)return this._smoothScrolling.dispose(),void(this._smoothScrolling=null);this._smoothScrolling.animationFrameDisposable=this._scheduleAtNextAnimationFrame(()=>{this._smoothScrolling&&(this._smoothScrolling.animationFrameDisposable=null,this._performSmoothScrolling())})}}_setState(e,t){let s=this._state;s.equals(e)||(this._state=e,this._onScroll.fire(this._state.createScrollEvent(s,t)))}},mo=class{constructor(e,t,s){this.scrollLeft=e,this.scrollTop=t,this.isDone=s}};function yo(e,t){let s=t-e;return function(t){return e+s*function(e){return 1-function(e){return Math.pow(e,3)}(1-e)}(t)}}var bo=class e{constructor(e,t,s,i){this.from=e,this.to=t,this.duration=i,this.startTime=s,this.animationFrameDisposable=null,this._initAnimations()}_initAnimations(){this.scrollLeft=this._initAnimation(this.from.scrollLeft,this.to.scrollLeft,this.to.width),this.scrollTop=this._initAnimation(this.from.scrollTop,this.to.scrollTop,this.to.height)}_initAnimation(e,t,s){if(Math.abs(e-t)>2.5*s){let i,r;return e<t?(i=e+.75*s,r=t-.75*s):(i=e-.75*s,r=t+.75*s),function(e,t,s){return function(i){return i<s?e(i/s):t((i-s)/(1-s))}}(yo(e,i),yo(r,t),.33)}return yo(e,t)}dispose(){null!==this.animationFrameDisposable&&(this.animationFrameDisposable.dispose(),this.animationFrameDisposable=null)}acceptScrollDimensions(e){this.to=e.withScrollPosition(this.to),this._initAnimations()}tick(){return this._tick(Date.now())}_tick(e){let t=(e-this.startTime)/this.duration;if(t<1){let e=this.scrollLeft(t),s=this.scrollTop(t);return new mo(e,s,!1)}return new mo(this.to.scrollLeft,this.to.scrollTop,!0)}combine(t,s,i){return e.start(t,s,i)}static start(t,s,i){i+=10;let r=Date.now()-10;return new e(t,s,r,i)}};var wo=class extends Dr{constructor(e,t,s){super(),this._visibility=e,this._visibleClassName=t,this._invisibleClassName=s,this._domNode=null,this._isVisible=!1,this._isNeeded=!1,this._rawShouldBeVisible=!1,this._shouldBeVisible=!1,this._revealTimer=this._register(new qn)}setVisibility(e){this._visibility!==e&&(this._visibility=e,this._updateShouldBeVisible())}setShouldBeVisible(e){this._rawShouldBeVisible=e,this._updateShouldBeVisible()}_applyVisibilitySetting(){return 2!==this._visibility&&(3===this._visibility||this._rawShouldBeVisible)}_updateShouldBeVisible(){let e=this._applyVisibilitySetting();this._shouldBeVisible!==e&&(this._shouldBeVisible=e,this.ensureVisibility())}setIsNeeded(e){this._isNeeded!==e&&(this._isNeeded=e,this.ensureVisibility())}setDomNode(e){this._domNode=e,this._domNode.setClassName(this._invisibleClassName),this.setShouldBeVisible(!1)}ensureVisibility(){this._isNeeded?this._shouldBeVisible?this._reveal():this._hide(!0):this._hide(!1)}_reveal(){this._isVisible||(this._isVisible=!0,this._revealTimer.setIfNotSet(()=>{this._domNode?.setClassName(this._visibleClassName)},0))}_hide(e){this._revealTimer.cancel(),this._isVisible&&(this._isVisible=!1,this._domNode?.setClassName(this._invisibleClassName+(e?" fade":"")))}},So=class extends _o{constructor(e){super(),this._lazyRender=e.lazyRender,this._host=e.host,this._scrollable=e.scrollable,this._scrollByPage=e.scrollByPage,this._scrollbarState=e.scrollbarState,this._visibilityController=this._register(new wo(e.visibility,"visible scrollbar "+e.extraScrollbarClassName,"invisible scrollbar "+e.extraScrollbarClassName)),this._visibilityController.setIsNeeded(this._scrollbarState.isNeeded()),this._pointerMoveMonitor=this._register(new co),this._shouldRender=!0,this.domNode=lo(document.createElement("div")),this.domNode.setAttribute("role","presentation"),this.domNode.setAttribute("aria-hidden","true"),this._visibilityController.setDomNode(this.domNode),this.domNode.setPosition("absolute"),this._register(eo(this.domNode.domNode,no.POINTER_DOWN,e=>this._domNodePointerDown(e)))}_createArrow(e){let t=this._register(new fo(e));this.domNode.domNode.appendChild(t.bgDomNode),this.domNode.domNode.appendChild(t.domNode)}_createSlider(e,t,s,i){this.slider=lo(document.createElement("div")),this.slider.setClassName("slider"),this.slider.setPosition("absolute"),this.slider.setTop(e),this.slider.setLeft(t),"number"==typeof s&&this.slider.setWidth(s),"number"==typeof i&&this.slider.setHeight(i),this.slider.setLayerHinting(!0),this.slider.setContain("strict"),this.domNode.domNode.appendChild(this.slider.domNode),this._register(eo(this.slider.domNode,no.POINTER_DOWN,e=>{0===e.button&&(e.preventDefault(),this._sliderPointerDown(e))})),this.onclick(this.slider.domNode,e=>{e.leftButton&&e.stopPropagation()})}_onElementSize(e){return this._scrollbarState.setVisibleSize(e)&&(this._visibilityController.setIsNeeded(this._scrollbarState.isNeeded()),this._shouldRender=!0,this._lazyRender||this.render()),this._shouldRender}_onElementScrollSize(e){return this._scrollbarState.setScrollSize(e)&&(this._visibilityController.setIsNeeded(this._scrollbarState.isNeeded()),this._shouldRender=!0,this._lazyRender||this.render()),this._shouldRender}_onElementScrollPosition(e){return this._scrollbarState.setScrollPosition(e)&&(this._visibilityController.setIsNeeded(this._scrollbarState.isNeeded()),this._shouldRender=!0,this._lazyRender||this.render()),this._shouldRender}beginReveal(){this._visibilityController.setShouldBeVisible(!0)}beginHide(){this._visibilityController.setShouldBeVisible(!1)}render(){this._shouldRender&&(this._shouldRender=!1,this._renderDomNode(this._scrollbarState.getRectangleLargeSize(),this._scrollbarState.getRectangleSmallSize()),this._updateSlider(this._scrollbarState.getSliderSize(),this._scrollbarState.getArrowSize()+this._scrollbarState.getSliderPosition()))}_domNodePointerDown(e){e.target===this.domNode.domNode&&this._onPointerDown(e)}delegatePointerDown(e){let t=this.domNode.domNode.getClientRects()[0].top,s=t+this._scrollbarState.getSliderPosition(),i=t+this._scrollbarState.getSliderPosition()+this._scrollbarState.getSliderSize(),r=this._sliderPointerPosition(e);s<=r&&r<=i?0===e.button&&(e.preventDefault(),this._sliderPointerDown(e)):this._onPointerDown(e)}_onPointerDown(e){let t,s;if(e.target===this.domNode.domNode&&"number"==typeof e.offsetX&&"number"==typeof e.offsetY)t=e.offsetX,s=e.offsetY;else{let i=function(e){let t=e.getBoundingClientRect(),s=Xn(e);return{left:t.left+s.scrollX,top:t.top+s.scrollY,width:t.width,height:t.height}}(this.domNode.domNode);t=e.pageX-i.left,s=e.pageY-i.top}let i=this._pointerDownRelativePosition(t,s);this._setDesiredScrollPositionNow(this._scrollByPage?this._scrollbarState.getDesiredScrollPositionFromOffsetPaged(i):this._scrollbarState.getDesiredScrollPositionFromOffset(i)),0===e.button&&(e.preventDefault(),this._sliderPointerDown(e))}_sliderPointerDown(e){if(!(e.target&&e.target instanceof Element))return;let t=this._sliderPointerPosition(e),s=this._sliderOrthogonalPointerPosition(e),i=this._scrollbarState.clone();this.slider.toggleClassName("active",!0),this._pointerMoveMonitor.startMonitoring(e.target,e.pointerId,e.buttons,e=>{let r=this._sliderOrthogonalPointerPosition(e),n=Math.abs(r-s);if(mn&&n>140)return void this._setDesiredScrollPositionNow(i.getScrollPosition());let o=this._sliderPointerPosition(e)-t;this._setDesiredScrollPositionNow(i.getDesiredScrollPositionFromDelta(o))},()=>{this.slider.toggleClassName("active",!1),this._host.onDragEnd()}),this._host.onDragStart()}_setDesiredScrollPositionNow(e){let t={};this.writeScrollPosition(t,e),this._scrollable.setScrollPositionNow(t)}updateScrollbarSize(e){this._updateScrollbarSize(e),this._scrollbarState.setScrollbarSize(e),this._shouldRender=!0,this._lazyRender||this.render()}isNeeded(){return this._scrollbarState.isNeeded()}},xo=class e{constructor(e,t,s,i,r,n){this._scrollbarSize=Math.round(t),this._oppositeScrollbarSize=Math.round(s),this._arrowSize=Math.round(e),this._visibleSize=i,this._scrollSize=r,this._scrollPosition=n,this._computedAvailableSize=0,this._computedIsNeeded=!1,this._computedSliderSize=0,this._computedSliderRatio=0,this._computedSliderPosition=0,this._refreshComputedValues()}clone(){return new e(this._arrowSize,this._scrollbarSize,this._oppositeScrollbarSize,this._visibleSize,this._scrollSize,this._scrollPosition)}setVisibleSize(e){let t=Math.round(e);return this._visibleSize!==t&&(this._visibleSize=t,this._refreshComputedValues(),!0)}setScrollSize(e){let t=Math.round(e);return this._scrollSize!==t&&(this._scrollSize=t,this._refreshComputedValues(),!0)}setScrollPosition(e){let t=Math.round(e);return this._scrollPosition!==t&&(this._scrollPosition=t,this._refreshComputedValues(),!0)}setScrollbarSize(e){this._scrollbarSize=Math.round(e)}setOppositeScrollbarSize(e){this._oppositeScrollbarSize=Math.round(e)}static _computeValues(e,t,s,i,r){let n=Math.max(0,s-e),o=Math.max(0,n-2*t),a=i>0&&i>s;if(!a)return{computedAvailableSize:Math.round(n),computedIsNeeded:a,computedSliderSize:Math.round(o),computedSliderRatio:0,computedSliderPosition:0};let l=Math.round(Math.max(20,Math.floor(s*o/i))),h=(o-l)/(i-s),c=r*h;return{computedAvailableSize:Math.round(n),computedIsNeeded:a,computedSliderSize:Math.round(l),computedSliderRatio:h,computedSliderPosition:Math.round(c)}}_refreshComputedValues(){let t=e._computeValues(this._oppositeScrollbarSize,this._arrowSize,this._visibleSize,this._scrollSize,this._scrollPosition);this._computedAvailableSize=t.computedAvailableSize,this._computedIsNeeded=t.computedIsNeeded,this._computedSliderSize=t.computedSliderSize,this._computedSliderRatio=t.computedSliderRatio,this._computedSliderPosition=t.computedSliderPosition}getArrowSize(){return this._arrowSize}getScrollPosition(){return this._scrollPosition}getRectangleLargeSize(){return this._computedAvailableSize}getRectangleSmallSize(){return this._scrollbarSize}isNeeded(){return this._computedIsNeeded}getSliderSize(){return this._computedSliderSize}getSliderPosition(){return this._computedSliderPosition}getDesiredScrollPositionFromOffset(e){if(!this._computedIsNeeded)return 0;let t=e-this._arrowSize-this._computedSliderSize/2;return Math.round(t/this._computedSliderRatio)}getDesiredScrollPositionFromOffsetPaged(e){if(!this._computedIsNeeded)return 0;let t=e-this._arrowSize,s=this._scrollPosition;return t<this._computedSliderPosition?s-=this._visibleSize:s+=this._visibleSize,s}getDesiredScrollPositionFromDelta(e){if(!this._computedIsNeeded)return 0;let t=this._computedSliderPosition+e;return Math.round(t/this._computedSliderRatio)}},$o=class extends So{constructor(e,t,s){let i=e.getScrollDimensions(),r=e.getCurrentScrollPosition();if(super({lazyRender:t.lazyRender,host:s,scrollbarState:new xo(t.horizontalHasArrows?t.arrowSize:0,2===t.horizontal?0:t.horizontalScrollbarSize,2===t.vertical?0:t.verticalScrollbarSize,i.width,i.scrollWidth,r.scrollLeft),visibility:t.horizontal,extraScrollbarClassName:"horizontal",scrollable:e,scrollByPage:t.scrollByPage}),t.horizontalHasArrows)throw new Error("horizontalHasArrows is not supported in xterm.js");this._createSlider(Math.floor((t.horizontalScrollbarSize-t.horizontalSliderSize)/2),0,void 0,t.horizontalSliderSize)}_updateSlider(e,t){this.slider.setWidth(e),this.slider.setLeft(t)}_renderDomNode(e,t){this.domNode.setWidth(e),this.domNode.setHeight(t),this.domNode.setLeft(0),this.domNode.setBottom(0)}onDidScroll(e){return this._shouldRender=this._onElementScrollSize(e.scrollWidth)||this._shouldRender,this._shouldRender=this._onElementScrollPosition(e.scrollLeft)||this._shouldRender,this._shouldRender=this._onElementSize(e.width)||this._shouldRender,this._shouldRender}_pointerDownRelativePosition(e,t){return e}_sliderPointerPosition(e){return e.pageX}_sliderOrthogonalPointerPosition(e){return e.pageY}_updateScrollbarSize(e){this.slider.setHeight(e)}writeScrollPosition(e,t){e.scrollLeft=t}updateOptions(e){this.updateScrollbarSize(2===e.horizontal?0:e.horizontalScrollbarSize),this._scrollbarState.setOppositeScrollbarSize(2===e.vertical?0:e.verticalScrollbarSize),this._visibilityController.setVisibility(e.horizontal),this._scrollByPage=e.scrollByPage}},ko=class extends So{constructor(e,t,s){let i=e.getScrollDimensions(),r=e.getCurrentScrollPosition();if(super({lazyRender:t.lazyRender,host:s,scrollbarState:new xo(t.verticalHasArrows?t.arrowSize:0,2===t.vertical?0:t.verticalScrollbarSize,0,i.height,i.scrollHeight,r.scrollTop),visibility:t.vertical,extraScrollbarClassName:"vertical",scrollable:e,scrollByPage:t.scrollByPage}),t.verticalHasArrows)throw new Error("horizontalHasArrows is not supported in xterm.js");this._createSlider(0,Math.floor((t.verticalScrollbarSize-t.verticalSliderSize)/2),t.verticalSliderSize,void 0)}_updateSlider(e,t){this.slider.setHeight(e),this.slider.setTop(t)}_renderDomNode(e,t){this.domNode.setWidth(t),this.domNode.setHeight(e),this.domNode.setRight(0),this.domNode.setTop(0)}onDidScroll(e){return this._shouldRender=this._onElementScrollSize(e.scrollHeight)||this._shouldRender,this._shouldRender=this._onElementScrollPosition(e.scrollTop)||this._shouldRender,this._shouldRender=this._onElementSize(e.height)||this._shouldRender,this._shouldRender}_pointerDownRelativePosition(e,t){return t}_sliderPointerPosition(e){return e.pageY}_sliderOrthogonalPointerPosition(e){return e.pageX}_updateScrollbarSize(e){this.slider.setWidth(e)}writeScrollPosition(e,t){e.scrollTop=t}updateOptions(e){this.updateScrollbarSize(2===e.vertical?0:e.verticalScrollbarSize),this._scrollbarState.setOppositeScrollbarSize(0),this._visibilityController.setVisibility(e.vertical),this._scrollByPage=e.scrollByPage}},Co=class{constructor(e,t,s){this.timestamp=e,this.deltaX=t,this.deltaY=s,this.score=0}},Eo=class{constructor(){this._capacity=5,this._memory=[],this._front=-1,this._rear=-1}isPhysicalMouseWheel(){if(-1===this._front&&-1===this._rear)return!1;let e=1,t=0,s=1,i=this._rear;for(;;){let r=i===this._front?e:Math.pow(2,-s);if(e-=r,t+=this._memory[i].score*r,i===this._front)break;i=(this._capacity+i-1)%this._capacity,s++}return t<=.5}acceptStandardWheelEvent(e){if(rn){let t=function(e){return Qr.INSTANCE.getZoomFactor(e)}(Xn(e.browserEvent));this.accept(Date.now(),e.deltaX*t,e.deltaY*t)}else this.accept(Date.now(),e.deltaX,e.deltaY)}accept(e,t,s){let i=null,r=new Co(e,t,s);-1===this._front&&-1===this._rear?(this._memory[0]=r,this._front=0,this._rear=0):(i=this._memory[this._rear],this._rear=(this._rear+1)%this._capacity,this._rear===this._front&&(this._front=(this._front+1)%this._capacity),this._memory[this._rear]=r),r.score=this._computeScore(r,i)}_computeScore(e,t){if(Math.abs(e.deltaX)>0&&Math.abs(e.deltaY)>0)return 1;let s=.5;if((!this._isAlmostInt(e.deltaX)||!this._isAlmostInt(e.deltaY))&&(s+=.25),t){let i=Math.abs(e.deltaX),r=Math.abs(e.deltaY),n=Math.abs(t.deltaX),o=Math.abs(t.deltaY),a=Math.max(Math.min(i,n),1),l=Math.max(Math.min(r,o),1),h=Math.max(i,n),c=Math.max(r,o);h%a===0&&c%l===0&&(s-=.5)}return Math.min(Math.max(s,0),1)}_isAlmostInt(e){return Math.abs(Math.round(e)-e)<.01}};Eo.INSTANCE=new Eo;var Ro=Eo,Po=class extends _o{constructor(e,t,s){super(),this._onScroll=this._register(new Xr),this.onScroll=this._onScroll.event,this._onWillScroll=this._register(new Xr),this.onWillScroll=this._onWillScroll.event,this._options=function(e){let t={lazyRender:typeof e.lazyRender<"u"&&e.lazyRender,className:typeof e.className<"u"?e.className:"",useShadows:!(typeof e.useShadows<"u")||e.useShadows,handleMouseWheel:!(typeof e.handleMouseWheel<"u")||e.handleMouseWheel,flipAxes:typeof e.flipAxes<"u"&&e.flipAxes,consumeMouseWheelIfScrollbarIsNeeded:typeof e.consumeMouseWheelIfScrollbarIsNeeded<"u"&&e.consumeMouseWheelIfScrollbarIsNeeded,alwaysConsumeMouseWheel:typeof e.alwaysConsumeMouseWheel<"u"&&e.alwaysConsumeMouseWheel,scrollYToX:typeof e.scrollYToX<"u"&&e.scrollYToX,mouseWheelScrollSensitivity:typeof e.mouseWheelScrollSensitivity<"u"?e.mouseWheelScrollSensitivity:1,fastScrollSensitivity:typeof e.fastScrollSensitivity<"u"?e.fastScrollSensitivity:5,scrollPredominantAxis:!(typeof e.scrollPredominantAxis<"u")||e.scrollPredominantAxis,mouseWheelSmoothScroll:!(typeof e.mouseWheelSmoothScroll<"u")||e.mouseWheelSmoothScroll,arrowSize:typeof e.arrowSize<"u"?e.arrowSize:11,listenOnDomNode:typeof e.listenOnDomNode<"u"?e.listenOnDomNode:null,horizontal:typeof e.horizontal<"u"?e.horizontal:1,horizontalScrollbarSize:typeof e.horizontalScrollbarSize<"u"?e.horizontalScrollbarSize:10,horizontalSliderSize:typeof e.horizontalSliderSize<"u"?e.horizontalSliderSize:0,horizontalHasArrows:typeof e.horizontalHasArrows<"u"&&e.horizontalHasArrows,vertical:typeof e.vertical<"u"?e.vertical:1,verticalScrollbarSize:typeof e.verticalScrollbarSize<"u"?e.verticalScrollbarSize:10,verticalHasArrows:typeof e.verticalHasArrows<"u"&&e.verticalHasArrows,verticalSliderSize:typeof e.verticalSliderSize<"u"?e.verticalSliderSize:0,scrollByPage:typeof e.scrollByPage<"u"&&e.scrollByPage};return t.horizontalSliderSize=typeof e.horizontalSliderSize<"u"?e.horizontalSliderSize:t.horizontalScrollbarSize,t.verticalSliderSize=typeof e.verticalSliderSize<"u"?e.verticalSliderSize:t.verticalScrollbarSize,yn&&(t.className+=" mac"),t}(t),this._scrollable=s,this._register(this._scrollable.onScroll(e=>{this._onWillScroll.fire(e),this._onDidScroll(e),this._onScroll.fire(e)}));let i={onMouseWheel:e=>this._onMouseWheel(e),onDragStart:()=>this._onDragStart(),onDragEnd:()=>this._onDragEnd()};this._verticalScrollbar=this._register(new ko(this._scrollable,this._options,i)),this._horizontalScrollbar=this._register(new $o(this._scrollable,this._options,i)),this._domNode=document.createElement("div"),this._domNode.className="xterm-scrollable-element "+this._options.className,this._domNode.setAttribute("role","presentation"),this._domNode.style.position="relative",this._domNode.appendChild(e),this._domNode.appendChild(this._horizontalScrollbar.domNode.domNode),this._domNode.appendChild(this._verticalScrollbar.domNode.domNode),this._options.useShadows?(this._leftShadowDomNode=lo(document.createElement("div")),this._leftShadowDomNode.setClassName("shadow"),this._domNode.appendChild(this._leftShadowDomNode.domNode),this._topShadowDomNode=lo(document.createElement("div")),this._topShadowDomNode.setClassName("shadow"),this._domNode.appendChild(this._topShadowDomNode.domNode),this._topLeftShadowDomNode=lo(document.createElement("div")),this._topLeftShadowDomNode.setClassName("shadow"),this._domNode.appendChild(this._topLeftShadowDomNode.domNode)):(this._leftShadowDomNode=null,this._topShadowDomNode=null,this._topLeftShadowDomNode=null),this._listenOnDomNode=this._options.listenOnDomNode||this._domNode,this._mouseWheelToDispose=[],this._setListeningToMouseWheel(this._options.handleMouseWheel),this.onmouseover(this._listenOnDomNode,e=>this._onMouseOver(e)),this.onmouseleave(this._listenOnDomNode,e=>this._onMouseLeave(e)),this._hideTimeout=this._register(new qn),this._isDragging=!1,this._mouseIsOver=!1,this._shouldRender=!0,this._revealOnScroll=!0}get options(){return this._options}dispose(){this._mouseWheelToDispose=Rr(this._mouseWheelToDispose),super.dispose()}getDomNode(){return this._domNode}getOverviewRulerLayoutInfo(){return{parent:this._domNode,insertBefore:this._verticalScrollbar.domNode.domNode}}delegateVerticalScrollbarPointerDown(e){this._verticalScrollbar.delegatePointerDown(e)}getScrollDimensions(){return this._scrollable.getScrollDimensions()}setScrollDimensions(e){this._scrollable.setScrollDimensions(e,!1)}updateClassName(e){this._options.className=e,yn&&(this._options.className+=" mac"),this._domNode.className="xterm-scrollable-element "+this._options.className}updateOptions(e){typeof e.handleMouseWheel<"u"&&(this._options.handleMouseWheel=e.handleMouseWheel,this._setListeningToMouseWheel(this._options.handleMouseWheel)),typeof e.mouseWheelScrollSensitivity<"u"&&(this._options.mouseWheelScrollSensitivity=e.mouseWheelScrollSensitivity),typeof e.fastScrollSensitivity<"u"&&(this._options.fastScrollSensitivity=e.fastScrollSensitivity),typeof e.scrollPredominantAxis<"u"&&(this._options.scrollPredominantAxis=e.scrollPredominantAxis),typeof e.horizontal<"u"&&(this._options.horizontal=e.horizontal),typeof e.vertical<"u"&&(this._options.vertical=e.vertical),typeof e.horizontalScrollbarSize<"u"&&(this._options.horizontalScrollbarSize=e.horizontalScrollbarSize),typeof e.verticalScrollbarSize<"u"&&(this._options.verticalScrollbarSize=e.verticalScrollbarSize),typeof e.scrollByPage<"u"&&(this._options.scrollByPage=e.scrollByPage),this._horizontalScrollbar.updateOptions(this._options),this._verticalScrollbar.updateOptions(this._options),this._options.lazyRender||this._render()}setRevealOnScroll(e){this._revealOnScroll=e}delegateScrollFromMouseWheelEvent(e){this._onMouseWheel(new Un(e))}_setListeningToMouseWheel(e){if(this._mouseWheelToDispose.length>0!==e&&(this._mouseWheelToDispose=Rr(this._mouseWheelToDispose),e)){let e=e=>{this._onMouseWheel(new Un(e))};this._mouseWheelToDispose.push(eo(this._listenOnDomNode,no.MOUSE_WHEEL,e,{passive:!1}))}}_onMouseWheel(e){if(e.browserEvent?.defaultPrevented)return;let t=Ro.INSTANCE;t.acceptStandardWheelEvent(e);let s=!1;if(e.deltaY||e.deltaX){let i=e.deltaY*this._options.mouseWheelScrollSensitivity,r=e.deltaX*this._options.mouseWheelScrollSensitivity;this._options.scrollPredominantAxis&&(this._options.scrollYToX&&r+i===0?r=i=0:Math.abs(i)>=Math.abs(r)?r=0:i=0),this._options.flipAxes&&([i,r]=[r,i]);let n=!yn&&e.browserEvent&&e.browserEvent.shiftKey;(this._options.scrollYToX||n)&&!r&&(r=i,i=0),e.browserEvent&&e.browserEvent.altKey&&(r*=this._options.fastScrollSensitivity,i*=this._options.fastScrollSensitivity);let o=this._scrollable.getFutureScrollPosition(),a={};if(i){let e=50*i,t=o.scrollTop-(e<0?Math.floor(e):Math.ceil(e));this._verticalScrollbar.writeScrollPosition(a,t)}if(r){let e=50*r,t=o.scrollLeft-(e<0?Math.floor(e):Math.ceil(e));this._horizontalScrollbar.writeScrollPosition(a,t)}a=this._scrollable.validateScrollPosition(a),(o.scrollLeft!==a.scrollLeft||o.scrollTop!==a.scrollTop)&&(this._options.mouseWheelSmoothScroll&&t.isPhysicalMouseWheel()?this._scrollable.setScrollPositionSmooth(a):this._scrollable.setScrollPositionNow(a),s=!0)}let i=s;!i&&this._options.alwaysConsumeMouseWheel&&(i=!0),!i&&this._options.consumeMouseWheelIfScrollbarIsNeeded&&(this._verticalScrollbar.isNeeded()||this._horizontalScrollbar.isNeeded())&&(i=!0),i&&(e.preventDefault(),e.stopPropagation())}_onDidScroll(e){this._shouldRender=this._horizontalScrollbar.onDidScroll(e)||this._shouldRender,this._shouldRender=this._verticalScrollbar.onDidScroll(e)||this._shouldRender,this._options.useShadows&&(this._shouldRender=!0),this._revealOnScroll&&this._reveal(),this._options.lazyRender||this._render()}renderNow(){if(!this._options.lazyRender)throw new Error("Please use `lazyRender` together with `renderNow`!");this._render()}_render(){if(this._shouldRender&&(this._shouldRender=!1,this._horizontalScrollbar.render(),this._verticalScrollbar.render(),this._options.useShadows)){let e=this._scrollable.getCurrentScrollPosition(),t=e.scrollTop>0,s=e.scrollLeft>0,i=s?" left":"",r=t?" top":"",n=s||t?" top-left-corner":"";this._leftShadowDomNode.setClassName(`shadow${i}`),this._topShadowDomNode.setClassName(`shadow${r}`),this._topLeftShadowDomNode.setClassName(`shadow${n}${r}${i}`)}}_onDragStart(){this._isDragging=!0,this._reveal()}_onDragEnd(){this._isDragging=!1,this._hide()}_onMouseLeave(e){this._mouseIsOver=!1,this._hide()}_onMouseOver(e){this._mouseIsOver=!0,this._reveal()}_reveal(){this._verticalScrollbar.beginReveal(),this._horizontalScrollbar.beginReveal(),this._scheduleHide()}_hide(){!this._mouseIsOver&&!this._isDragging&&(this._verticalScrollbar.beginHide(),this._horizontalScrollbar.beginHide())}_scheduleHide(){!this._mouseIsOver&&!this._isDragging&&this._hideTimeout.cancelAndSet(()=>this._hide(),500)}},Ao=class extends Po{constructor(e,t,s){super(e,t,s)}setScrollPosition(e){e.reuseAnimation?this._scrollable.setScrollPositionSmooth(e,e.reuseAnimation):this._scrollable.setScrollPositionNow(e)}getScrollPosition(){return this._scrollable.getCurrentScrollPosition()}};var To=class extends Dr{constructor(e,t,s,i,r,n,o,a){super(),this._bufferService=s,this._optionsService=o,this._renderService=a,this._onRequestScrollLines=this._register(new Xr),this.onRequestScrollLines=this._onRequestScrollLines.event,this._isSyncing=!1,this._isHandlingScroll=!1,this._suppressOnScrollHandler=!1;let l=this._register(new vo({forceIntegerValues:!1,smoothScrollDuration:this._optionsService.rawOptions.smoothScrollDuration,scheduleAtNextAnimationFrame:e=>to(i.window,e)}));this._register(this._optionsService.onSpecificOptionChange("smoothScrollDuration",()=>{l.setSmoothScrollDuration(this._optionsService.rawOptions.smoothScrollDuration)})),this._scrollableElement=this._register(new Ao(t,{vertical:1,horizontal:2,useShadows:!1,mouseWheelSmoothScroll:!0,...this._getChangeOptions()},l)),this._register(this._optionsService.onMultipleOptionChange(["scrollSensitivity","fastScrollSensitivity","overviewRuler"],()=>this._scrollableElement.updateOptions(this._getChangeOptions()))),this._register(r.onProtocolChange(e=>{this._scrollableElement.updateOptions({handleMouseWheel:!(16&e)})})),this._scrollableElement.setScrollDimensions({height:0,scrollHeight:0}),this._register(Or.runAndSubscribe(n.onChangeColors,()=>{this._scrollableElement.getDomNode().style.backgroundColor=n.colors.background.css})),e.appendChild(this._scrollableElement.getDomNode()),this._register(Pr(()=>this._scrollableElement.getDomNode().remove())),this._styleElement=i.mainDocument.createElement("style"),t.appendChild(this._styleElement),this._register(Pr(()=>this._styleElement.remove())),this._register(Or.runAndSubscribe(n.onChangeColors,()=>{this._styleElement.textContent=[".xterm .xterm-scrollable-element > .scrollbar > .slider {",`  background: ${n.colors.scrollbarSliderBackground.css};`,"}",".xterm .xterm-scrollable-element > .scrollbar > .slider:hover {",`  background: ${n.colors.scrollbarSliderHoverBackground.css};`,"}",".xterm .xterm-scrollable-element > .scrollbar > .slider.active {",`  background: ${n.colors.scrollbarSliderActiveBackground.css};`,"}"].join("\n")})),this._register(this._bufferService.onResize(()=>this.queueSync())),this._register(this._bufferService.buffers.onBufferActivate(()=>{this._latestYDisp=void 0,this.queueSync()})),this._register(this._bufferService.onScroll(()=>this._sync())),this._register(this._scrollableElement.onScroll(e=>this._handleScroll(e)))}scrollLines(e){let t=this._scrollableElement.getScrollPosition();this._scrollableElement.setScrollPosition({reuseAnimation:!0,scrollTop:t.scrollTop+e*this._renderService.dimensions.css.cell.height})}scrollToLine(e,t){t&&(this._latestYDisp=e),this._scrollableElement.setScrollPosition({reuseAnimation:!t,scrollTop:e*this._renderService.dimensions.css.cell.height})}_getChangeOptions(){return{mouseWheelScrollSensitivity:this._optionsService.rawOptions.scrollSensitivity,fastScrollSensitivity:this._optionsService.rawOptions.fastScrollSensitivity,verticalScrollbarSize:this._optionsService.rawOptions.overviewRuler?.width||14}}queueSync(e){void 0!==e&&(this._latestYDisp=e),void 0===this._queuedAnimationFrame&&(this._queuedAnimationFrame=this._renderService.addRefreshCallback(()=>{this._queuedAnimationFrame=void 0,this._sync(this._latestYDisp)}))}_sync(e=this._bufferService.buffer.ydisp){!this._renderService||this._isSyncing||(this._isSyncing=!0,this._suppressOnScrollHandler=!0,this._scrollableElement.setScrollDimensions({height:this._renderService.dimensions.css.canvas.height,scrollHeight:this._renderService.dimensions.css.cell.height*this._bufferService.buffer.lines.length}),this._suppressOnScrollHandler=!1,e!==this._latestYDisp&&this._scrollableElement.setScrollPosition({scrollTop:e*this._renderService.dimensions.css.cell.height}),this._isSyncing=!1)}_handleScroll(e){if(!this._renderService||this._isHandlingScroll||this._suppressOnScrollHandler)return;this._isHandlingScroll=!0;let t=Math.round(e.scrollTop/this._renderService.dimensions.css.cell.height),s=t-this._bufferService.buffer.ydisp;0!==s&&(this._latestYDisp=t,this._onRequestScrollLines.fire(s)),this._isHandlingScroll=!1}};To=Pi([Ai(2,Zi),Ai(3,dr),Ai(4,Qi),Ai(5,gr),Ai(6,rr),Ai(7,pr)],To);var Do=class extends Dr{constructor(e,t,s,i,r){super(),this._screenElement=e,this._bufferService=t,this._coreBrowserService=s,this._decorationService=i,this._renderService=r,this._decorationElements=new Map,this._altBufferIsActive=!1,this._dimensionsChanged=!1,this._container=document.createElement("div"),this._container.classList.add("xterm-decoration-container"),this._screenElement.appendChild(this._container),this._register(this._renderService.onRenderedViewportChange(()=>this._doRefreshDecorations())),this._register(this._renderService.onDimensionsChange(()=>{this._dimensionsChanged=!0,this._queueRefresh()})),this._register(this._coreBrowserService.onDprChange(()=>this._queueRefresh())),this._register(this._bufferService.buffers.onBufferActivate(()=>{this._altBufferIsActive=this._bufferService.buffer===this._bufferService.buffers.alt})),this._register(this._decorationService.onDecorationRegistered(()=>this._queueRefresh())),this._register(this._decorationService.onDecorationRemoved(e=>this._removeDecoration(e))),this._register(Pr(()=>{this._container.remove(),this._decorationElements.clear()}))}_queueRefresh(){void 0===this._animationFrame&&(this._animationFrame=this._renderService.addRefreshCallback(()=>{this._doRefreshDecorations(),this._animationFrame=void 0}))}_doRefreshDecorations(){for(let e of this._decorationService.decorations)this._renderDecoration(e);this._dimensionsChanged=!1}_renderDecoration(e){this._refreshStyle(e),this._dimensionsChanged&&this._refreshXPosition(e)}_createElement(e){let t=this._coreBrowserService.mainDocument.createElement("div");t.classList.add("xterm-decoration"),t.classList.toggle("xterm-decoration-top-layer","top"===e?.options?.layer),t.style.width=`${Math.round((e.options.width||1)*this._renderService.dimensions.css.cell.width)}px`,t.style.height=(e.options.height||1)*this._renderService.dimensions.css.cell.height+"px",t.style.top=(e.marker.line-this._bufferService.buffers.active.ydisp)*this._renderService.dimensions.css.cell.height+"px",t.style.lineHeight=`${this._renderService.dimensions.css.cell.height}px`;let s=e.options.x??0;return s&&s>this._bufferService.cols&&(t.style.display="none"),this._refreshXPosition(e,t),t}_refreshStyle(e){let t=e.marker.line-this._bufferService.buffers.active.ydisp;if(t<0||t>=this._bufferService.rows)e.element&&(e.element.style.display="none",e.onRenderEmitter.fire(e.element));else{let s=this._decorationElements.get(e);s||(s=this._createElement(e),e.element=s,this._decorationElements.set(e,s),this._container.appendChild(s),e.onDispose(()=>{this._decorationElements.delete(e),s.remove()})),s.style.display=this._altBufferIsActive?"none":"block",this._altBufferIsActive||(s.style.width=`${Math.round((e.options.width||1)*this._renderService.dimensions.css.cell.width)}px`,s.style.height=(e.options.height||1)*this._renderService.dimensions.css.cell.height+"px",s.style.top=t*this._renderService.dimensions.css.cell.height+"px",s.style.lineHeight=`${this._renderService.dimensions.css.cell.height}px`),e.onRenderEmitter.fire(s)}}_refreshXPosition(e,t=e.element){if(!t)return;let s=e.options.x??0;"right"===(e.options.anchor||"left")?t.style.right=s?s*this._renderService.dimensions.css.cell.width+"px":"":t.style.left=s?s*this._renderService.dimensions.css.cell.width+"px":""}_removeDecoration(e){this._decorationElements.get(e)?.remove(),this._decorationElements.delete(e),e.dispose()}};Do=Pi([Ai(1,Zi),Ai(2,dr),Ai(3,ar),Ai(4,pr)],Do);var Lo,Mo,Bo,Oo=class{constructor(){this._zones=[],this._zonePool=[],this._zonePoolIndex=0,this._linePadding={full:0,left:0,center:0,right:0}}get zones(){return this._zonePool.length=Math.min(this._zonePool.length,this._zones.length),this._zones}clear(){this._zones.length=0,this._zonePoolIndex=0}addDecoration(e){if(e.options.overviewRulerOptions){for(let t of this._zones)if(t.color===e.options.overviewRulerOptions.color&&t.position===e.options.overviewRulerOptions.position){if(this._lineIntersectsZone(t,e.marker.line))return;if(this._lineAdjacentToZone(t,e.marker.line,e.options.overviewRulerOptions.position))return void this._addLineToZone(t,e.marker.line)}if(this._zonePoolIndex<this._zonePool.length)return this._zonePool[this._zonePoolIndex].color=e.options.overviewRulerOptions.color,this._zonePool[this._zonePoolIndex].position=e.options.overviewRulerOptions.position,this._zonePool[this._zonePoolIndex].startBufferLine=e.marker.line,this._zonePool[this._zonePoolIndex].endBufferLine=e.marker.line,void this._zones.push(this._zonePool[this._zonePoolIndex++]);this._zones.push({color:e.options.overviewRulerOptions.color,position:e.options.overviewRulerOptions.position,startBufferLine:e.marker.line,endBufferLine:e.marker.line}),this._zonePool.push(this._zones[this._zones.length-1]),this._zonePoolIndex++}}setPadding(e){this._linePadding=e}_lineIntersectsZone(e,t){return t>=e.startBufferLine&&t<=e.endBufferLine}_lineAdjacentToZone(e,t,s){return t>=e.startBufferLine-this._linePadding[s||"full"]&&t<=e.endBufferLine+this._linePadding[s||"full"]}_addLineToZone(e,t){e.startBufferLine=Math.min(e.startBufferLine,t),e.endBufferLine=Math.max(e.endBufferLine,t)}},zo={full:0,left:0,center:0,right:0},Io={full:0,left:0,center:0,right:0},No={full:0,left:0,center:0,right:0},Fo=class extends Dr{constructor(e,t,s,i,r,n,o,a){super(),this._viewportElement=e,this._screenElement=t,this._bufferService=s,this._decorationService=i,this._renderService=r,this._optionsService=n,this._themeService=o,this._coreBrowserService=a,this._colorZoneStore=new Oo,this._shouldUpdateDimensions=!0,this._shouldUpdateAnchor=!0,this._lastKnownBufferLength=0,this._canvas=this._coreBrowserService.mainDocument.createElement("canvas"),this._canvas.classList.add("xterm-decoration-overview-ruler"),this._refreshCanvasDimensions(),this._viewportElement.parentElement?.insertBefore(this._canvas,this._viewportElement),this._register(Pr(()=>this._canvas?.remove()));let l=this._canvas.getContext("2d");if(!l)throw new Error("Ctx cannot be null");this._ctx=l,this._register(this._decorationService.onDecorationRegistered(()=>this._queueRefresh(void 0,!0))),this._register(this._decorationService.onDecorationRemoved(()=>this._queueRefresh(void 0,!0))),this._register(this._renderService.onRenderedViewportChange(()=>this._queueRefresh())),this._register(this._bufferService.buffers.onBufferActivate(()=>{this._canvas.style.display=this._bufferService.buffer===this._bufferService.buffers.alt?"none":"block"})),this._register(this._bufferService.onScroll(()=>{this._lastKnownBufferLength!==this._bufferService.buffers.normal.lines.length&&(this._refreshDrawHeightConstants(),this._refreshColorZonePadding())})),this._register(this._renderService.onRender(()=>{(!this._containerHeight||this._containerHeight!==this._screenElement.clientHeight)&&(this._queueRefresh(!0),this._containerHeight=this._screenElement.clientHeight)})),this._register(this._coreBrowserService.onDprChange(()=>this._queueRefresh(!0))),this._register(this._optionsService.onSpecificOptionChange("overviewRuler",()=>this._queueRefresh(!0))),this._register(this._themeService.onChangeColors(()=>this._queueRefresh())),this._queueRefresh(!0)}get _width(){return this._optionsService.options.overviewRuler?.width||0}_refreshDrawConstants(){let e=Math.floor((this._canvas.width-1)/3),t=Math.ceil((this._canvas.width-1)/3);Io.full=this._canvas.width,Io.left=e,Io.center=t,Io.right=e,this._refreshDrawHeightConstants(),No.full=1,No.left=1,No.center=1+Io.left,No.right=1+Io.left+Io.center}_refreshDrawHeightConstants(){zo.full=Math.round(2*this._coreBrowserService.dpr);let e=this._canvas.height/this._bufferService.buffer.lines.length,t=Math.round(Math.max(Math.min(e,12),6)*this._coreBrowserService.dpr);zo.left=t,zo.center=t,zo.right=t}_refreshColorZonePadding(){this._colorZoneStore.setPadding({full:Math.floor(this._bufferService.buffers.active.lines.length/(this._canvas.height-1)*zo.full),left:Math.floor(this._bufferService.buffers.active.lines.length/(this._canvas.height-1)*zo.left),center:Math.floor(this._bufferService.buffers.active.lines.length/(this._canvas.height-1)*zo.center),right:Math.floor(this._bufferService.buffers.active.lines.length/(this._canvas.height-1)*zo.right)}),this._lastKnownBufferLength=this._bufferService.buffers.normal.lines.length}_refreshCanvasDimensions(){this._canvas.style.width=`${this._width}px`,this._canvas.width=Math.round(this._width*this._coreBrowserService.dpr),this._canvas.style.height=`${this._screenElement.clientHeight}px`,this._canvas.height=Math.round(this._screenElement.clientHeight*this._coreBrowserService.dpr),this._refreshDrawConstants(),this._refreshColorZonePadding()}_refreshDecorations(){this._shouldUpdateDimensions&&this._refreshCanvasDimensions(),this._ctx.clearRect(0,0,this._canvas.width,this._canvas.height),this._colorZoneStore.clear();for(let e of this._decorationService.decorations)this._colorZoneStore.addDecoration(e);this._ctx.lineWidth=1,this._renderRulerOutline();let e=this._colorZoneStore.zones;for(let t of e)"full"!==t.position&&this._renderColorZone(t);for(let t of e)"full"===t.position&&this._renderColorZone(t);this._shouldUpdateDimensions=!1,this._shouldUpdateAnchor=!1}_renderRulerOutline(){this._ctx.fillStyle=this._themeService.colors.overviewRulerBorder.css,this._ctx.fillRect(0,0,1,this._canvas.height),this._optionsService.rawOptions.overviewRuler.showTopBorder&&this._ctx.fillRect(1,0,this._canvas.width-1,1),this._optionsService.rawOptions.overviewRuler.showBottomBorder&&this._ctx.fillRect(1,this._canvas.height-1,this._canvas.width-1,this._canvas.height)}_renderColorZone(e){this._ctx.fillStyle=e.color,this._ctx.fillRect(No[e.position||"full"],Math.round((this._canvas.height-1)*(e.startBufferLine/this._bufferService.buffers.active.lines.length)-zo[e.position||"full"]/2),Io[e.position||"full"],Math.round((this._canvas.height-1)*((e.endBufferLine-e.startBufferLine)/this._bufferService.buffers.active.lines.length)+zo[e.position||"full"]))}_queueRefresh(e,t){this._shouldUpdateDimensions=e||this._shouldUpdateDimensions,this._shouldUpdateAnchor=t||this._shouldUpdateAnchor,void 0===this._animationFrame&&(this._animationFrame=this._coreBrowserService.window.requestAnimationFrame(()=>{this._refreshDecorations(),this._animationFrame=void 0}))}};Fo=Pi([Ai(2,Zi),Ai(3,ar),Ai(4,pr),Ai(5,rr),Ai(6,gr),Ai(7,dr)],Fo),(e=>{e.NUL="\0",e.SOH="",e.STX="",e.ETX="",e.EOT="",e.ENQ="",e.ACK="",e.BEL="",e.BS="\b",e.HT="\t",e.LF="\n",e.VT="\v",e.FF="\f",e.CR="\r",e.SO="",e.SI="",e.DLE="",e.DC1="",e.DC2="",e.DC3="",e.DC4="",e.NAK="",e.SYN="",e.ETB="",e.CAN="",e.EM="",e.SUB="",e.ESC="",e.FS="",e.GS="",e.RS="",e.US="",e.SP=" ",e.DEL=""})(Lo||={}),(e=>{e.PAD="",e.HOP="",e.BPH="",e.NBH="",e.IND="",e.NEL="",e.SSA="",e.ESA="",e.HTS="",e.HTJ="",e.VTS="",e.PLD="",e.PLU="",e.RI="",e.SS2="",e.SS3="",e.DCS="",e.PU1="",e.PU2="",e.STS="",e.CCH="",e.MW="",e.SPA="",e.EPA="",e.SOS="",e.SGCI="",e.SCI="",e.CSI="",e.ST="",e.OSC="",e.PM="",e.APC=""})(Mo||={}),(Bo||={}).ST=`${Lo.ESC}\\`;var Ho=class{constructor(e,t,s,i,r,n){this._textarea=e,this._compositionView=t,this._bufferService=s,this._optionsService=i,this._coreService=r,this._renderService=n,this._isComposing=!1,this._isSendingComposition=!1,this._compositionPosition={start:0,end:0},this._dataAlreadySent=""}get isComposing(){return this._isComposing}compositionstart(){this._isComposing=!0,this._compositionPosition.start=this._textarea.value.length,this._compositionView.textContent="",this._dataAlreadySent="",this._compositionView.classList.add("active")}compositionupdate(e){this._compositionView.textContent=e.data,this.updateCompositionElements(),setTimeout(()=>{this._compositionPosition.end=this._textarea.value.length},0)}compositionend(){this._finalizeComposition(!0)}keydown(e){if(this._isComposing||this._isSendingComposition){if(20===e.keyCode||229===e.keyCode||16===e.keyCode||17===e.keyCode||18===e.keyCode)return!1;this._finalizeComposition(!1)}return 229!==e.keyCode||(this._handleAnyTextareaChanges(),!1)}_finalizeComposition(e){if(this._compositionView.classList.remove("active"),this._isComposing=!1,e){let e={start:this._compositionPosition.start,end:this._compositionPosition.end};this._isSendingComposition=!0,setTimeout(()=>{if(this._isSendingComposition){let t;this._isSendingComposition=!1,e.start+=this._dataAlreadySent.length,t=this._isComposing?this._textarea.value.substring(e.start,this._compositionPosition.start):this._textarea.value.substring(e.start),t.length>0&&this._coreService.triggerDataEvent(t,!0)}},0)}else{this._isSendingComposition=!1;let e=this._textarea.value.substring(this._compositionPosition.start,this._compositionPosition.end);this._coreService.triggerDataEvent(e,!0)}}_handleAnyTextareaChanges(){let e=this._textarea.value;setTimeout(()=>{if(!this._isComposing){let t=this._textarea.value,s=t.replace(e,"");this._dataAlreadySent=s,t.length>e.length?this._coreService.triggerDataEvent(s,!0):t.length<e.length?this._coreService.triggerDataEvent(`${Lo.DEL}`,!0):t.length===e.length&&t!==e&&this._coreService.triggerDataEvent(t,!0)}},0)}updateCompositionElements(e){if(this._isComposing){if(this._bufferService.buffer.isCursorInViewport){let e=Math.min(this._bufferService.buffer.x,this._bufferService.cols-1),t=this._renderService.dimensions.css.cell.height,s=this._bufferService.buffer.y*this._renderService.dimensions.css.cell.height,i=e*this._renderService.dimensions.css.cell.width;this._compositionView.style.left=i+"px",this._compositionView.style.top=s+"px",this._compositionView.style.height=t+"px",this._compositionView.style.lineHeight=t+"px",this._compositionView.style.fontFamily=this._optionsService.rawOptions.fontFamily,this._compositionView.style.fontSize=this._optionsService.rawOptions.fontSize+"px";let r=this._compositionView.getBoundingClientRect();this._textarea.style.left=i+"px",this._textarea.style.top=s+"px",this._textarea.style.width=Math.max(r.width,1)+"px",this._textarea.style.height=Math.max(r.height,1)+"px",this._textarea.style.lineHeight=r.height+"px"}e||setTimeout(()=>this.updateCompositionElements(!0),0)}}};Ho=Pi([Ai(2,Zi),Ai(3,rr),Ai(4,er),Ai(5,pr)],Ho);var Wo,Uo,Ko,Vo,jo,qo=0,Yo=0,Go=0,Xo=0,Jo={css:"#00000000",rgba:0};function Zo(e){let t=e.toString(16);return t.length<2?"0"+t:t}function Qo(e,t){return e<t?(t+.05)/(e+.05):(e+.05)/(t+.05)}(e=>{e.toCss=function(e,t,s,i){return void 0!==i?`#${Zo(e)}${Zo(t)}${Zo(s)}${Zo(i)}`:`#${Zo(e)}${Zo(t)}${Zo(s)}`},e.toRgba=function(e,t,s,i=255){return(e<<24|t<<16|s<<8|i)>>>0},e.toColor=function(t,s,i,r){return{css:e.toCss(t,s,i,r),rgba:e.toRgba(t,s,i,r)}}})(Wo||={}),(e=>{function t(e,t){return Xo=Math.round(255*t),[qo,Yo,Go]=jo.toChannels(e.rgba),{css:Wo.toCss(qo,Yo,Go,Xo),rgba:Wo.toRgba(qo,Yo,Go,Xo)}}e.blend=function(e,t){if(1===(Xo=(255&t.rgba)/255))return{css:t.css,rgba:t.rgba};let s=t.rgba>>24&255,i=t.rgba>>16&255,r=t.rgba>>8&255,n=e.rgba>>24&255,o=e.rgba>>16&255,a=e.rgba>>8&255;return qo=n+Math.round((s-n)*Xo),Yo=o+Math.round((i-o)*Xo),Go=a+Math.round((r-a)*Xo),{css:Wo.toCss(qo,Yo,Go),rgba:Wo.toRgba(qo,Yo,Go)}},e.isOpaque=function(e){return!(255&~e.rgba)},e.ensureContrastRatio=function(e,t,s){let i=jo.ensureContrastRatio(e.rgba,t.rgba,s);if(i)return Wo.toColor(i>>24&255,i>>16&255,i>>8&255)},e.opaque=function(e){let t=(255|e.rgba)>>>0;return[qo,Yo,Go]=jo.toChannels(t),{css:Wo.toCss(qo,Yo,Go),rgba:t}},e.opacity=t,e.multiplyOpacity=function(e,s){return t(e,(Xo=255&e.rgba)*s/255)},e.toColorRGB=function(e){return[e.rgba>>24&255,e.rgba>>16&255,e.rgba>>8&255]}})(Uo||={}),(e=>{let t,s;try{let e=document.createElement("canvas");e.width=1,e.height=1;let i=e.getContext("2d",{willReadFrequently:!0});i&&(t=i,t.globalCompositeOperation="copy",s=t.createLinearGradient(0,0,1,1))}catch{}e.toColor=function(e){if(e.match(/#[\da-f]{3,8}/i))switch(e.length){case 4:return qo=parseInt(e.slice(1,2).repeat(2),16),Yo=parseInt(e.slice(2,3).repeat(2),16),Go=parseInt(e.slice(3,4).repeat(2),16),Wo.toColor(qo,Yo,Go);case 5:return qo=parseInt(e.slice(1,2).repeat(2),16),Yo=parseInt(e.slice(2,3).repeat(2),16),Go=parseInt(e.slice(3,4).repeat(2),16),Xo=parseInt(e.slice(4,5).repeat(2),16),Wo.toColor(qo,Yo,Go,Xo);case 7:return{css:e,rgba:(parseInt(e.slice(1),16)<<8|255)>>>0};case 9:return{css:e,rgba:parseInt(e.slice(1),16)>>>0}}let i=e.match(/rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(,\s*(0|1|\d?\.(\d+))\s*)?\)/);if(i)return qo=parseInt(i[1]),Yo=parseInt(i[2]),Go=parseInt(i[3]),Xo=Math.round(255*(void 0===i[5]?1:parseFloat(i[5]))),Wo.toColor(qo,Yo,Go,Xo);if(!t||!s)throw new Error("css.toColor: Unsupported css format");if(t.fillStyle=s,t.fillStyle=e,"string"!=typeof t.fillStyle)throw new Error("css.toColor: Unsupported css format");if(t.fillRect(0,0,1,1),[qo,Yo,Go,Xo]=t.getImageData(0,0,1,1).data,255!==Xo)throw new Error("css.toColor: Unsupported css format");return{rgba:Wo.toRgba(qo,Yo,Go,Xo),css:e}}})(Ko||={}),(e=>{function t(e,t,s){let i=e/255,r=t/255,n=s/255;return.2126*(i<=.03928?i/12.92:Math.pow((i+.055)/1.055,2.4))+.7152*(r<=.03928?r/12.92:Math.pow((r+.055)/1.055,2.4))+.0722*(n<=.03928?n/12.92:Math.pow((n+.055)/1.055,2.4))}e.relativeLuminance=function(e){return t(e>>16&255,e>>8&255,255&e)},e.relativeLuminance2=t})(Vo||={}),(e=>{function t(e,t,s){let i=e>>24&255,r=e>>16&255,n=e>>8&255,o=t>>24&255,a=t>>16&255,l=t>>8&255,h=Qo(Vo.relativeLuminance2(o,a,l),Vo.relativeLuminance2(i,r,n));for(;h<s&&(o>0||a>0||l>0);)o-=Math.max(0,Math.ceil(.1*o)),a-=Math.max(0,Math.ceil(.1*a)),l-=Math.max(0,Math.ceil(.1*l)),h=Qo(Vo.relativeLuminance2(o,a,l),Vo.relativeLuminance2(i,r,n));return(o<<24|a<<16|l<<8|255)>>>0}function s(e,t,s){let i=e>>24&255,r=e>>16&255,n=e>>8&255,o=t>>24&255,a=t>>16&255,l=t>>8&255,h=Qo(Vo.relativeLuminance2(o,a,l),Vo.relativeLuminance2(i,r,n));for(;h<s&&(o<255||a<255||l<255);)o=Math.min(255,o+Math.ceil(.1*(255-o))),a=Math.min(255,a+Math.ceil(.1*(255-a))),l=Math.min(255,l+Math.ceil(.1*(255-l))),h=Qo(Vo.relativeLuminance2(o,a,l),Vo.relativeLuminance2(i,r,n));return(o<<24|a<<16|l<<8|255)>>>0}e.blend=function(e,t){if(1===(Xo=(255&t)/255))return t;let s=t>>24&255,i=t>>16&255,r=t>>8&255,n=e>>24&255,o=e>>16&255,a=e>>8&255;return qo=n+Math.round((s-n)*Xo),Yo=o+Math.round((i-o)*Xo),Go=a+Math.round((r-a)*Xo),Wo.toRgba(qo,Yo,Go)},e.ensureContrastRatio=function(e,i,r){let n=Vo.relativeLuminance(e>>8),o=Vo.relativeLuminance(i>>8);if(Qo(n,o)<r){if(o<n){let o=t(e,i,r),a=Qo(n,Vo.relativeLuminance(o>>8));if(a<r){let t=s(e,i,r);return a>Qo(n,Vo.relativeLuminance(t>>8))?o:t}return o}let a=s(e,i,r),l=Qo(n,Vo.relativeLuminance(a>>8));if(l<r){let s=t(e,i,r);return l>Qo(n,Vo.relativeLuminance(s>>8))?a:s}return a}},e.reduceLuminance=t,e.increaseLuminance=s,e.toChannels=function(e){return[e>>24&255,e>>16&255,e>>8&255,255&e]}})(jo||={});var ea=class extends Vi{constructor(e,t,s){super(),this.content=0,this.combinedData="",this.fg=e.fg,this.bg=e.bg,this.combinedData=t,this._width=s}isCombined(){return 2097152}getWidth(){return this._width}getChars(){return this.combinedData}getCode(){return 2097151}setFromCharData(e){throw new Error("not implemented")}getAsCharData(){return[this.fg,this.getChars(),this.getWidth(),this.getCode()]}},ta=class{constructor(e){this._bufferService=e,this._characterJoiners=[],this._nextCharacterJoinerId=0,this._workCell=new qi}register(e){let t={id:this._nextCharacterJoinerId++,handler:e};return this._characterJoiners.push(t),t.id}deregister(e){for(let t=0;t<this._characterJoiners.length;t++)if(this._characterJoiners[t].id===e)return this._characterJoiners.splice(t,1),!0;return!1}getJoinedCharacters(e){if(0===this._characterJoiners.length)return[];let t=this._bufferService.buffer.lines.get(e);if(!t||0===t.length)return[];let s=[],i=t.translateToString(!0),r=0,n=0,o=0,a=t.getFg(0),l=t.getBg(0);for(let e=0;e<t.getTrimmedLength();e++)if(t.loadCell(e,this._workCell),0!==this._workCell.getWidth()){if(this._workCell.fg!==a||this._workCell.bg!==l){if(e-r>1){let e=this._getJoinedRanges(i,o,n,t,r);for(let t=0;t<e.length;t++)s.push(e[t])}r=e,o=n,a=this._workCell.fg,l=this._workCell.bg}n+=this._workCell.getChars().length||1}if(this._bufferService.cols-r>1){let e=this._getJoinedRanges(i,o,n,t,r);for(let t=0;t<e.length;t++)s.push(e[t])}return s}_getJoinedRanges(e,t,s,i,r){let n=e.substring(t,s),o=[];try{o=this._characterJoiners[0].handler(n)}catch(e){console.error(e)}for(let e=1;e<this._characterJoiners.length;e++)try{let t=this._characterJoiners[e].handler(n);for(let e=0;e<t.length;e++)ta._mergeRanges(o,t[e])}catch(e){console.error(e)}return this._stringRangesToCellRanges(o,i,r),o}_stringRangesToCellRanges(e,t,s){let i=0,r=!1,n=0,o=e[i];if(o){for(let a=s;a<this._bufferService.cols;a++){let s=t.getWidth(a),l=t.getString(a).length||1;if(0!==s){if(!r&&o[0]<=n&&(o[0]=a,r=!0),o[1]<=n){if(o[1]=a,o=e[++i],!o)break;o[0]<=n?(o[0]=a,r=!0):r=!1}n+=l}}o&&(o[1]=this._bufferService.cols)}}static _mergeRanges(e,t){let s=!1;for(let i=0;i<e.length;i++){let r=e[i];if(s){if(t[1]<=r[0])return e[i-1][1]=t[1],e;if(t[1]<=r[1])return e[i-1][1]=Math.max(t[1],r[1]),e.splice(i,1),e;e.splice(i,1),i--}else{if(t[1]<=r[0])return e.splice(i,0,t),e;if(t[1]<=r[1])return r[0]=Math.min(t[0],r[0]),e;t[0]<r[1]&&(r[0]=Math.min(t[0],r[0]),s=!0)}}return s?e[e.length-1][1]=t[1]:e.push(t),e}};ta=Pi([Ai(0,Zi)],ta);var sa=class{constructor(e,t,s,i,r,n,o){this._document=e,this._characterJoinerService=t,this._optionsService=s,this._coreBrowserService=i,this._coreService=r,this._decorationService=n,this._themeService=o,this._workCell=new qi,this._columnSelectMode=!1,this.defaultSpacing=0}handleSelectionChanged(e,t,s){this._selectionStart=e,this._selectionEnd=t,this._columnSelectMode=s}createRow(e,t,s,i,r,n,o,a,l,h,c){let d=[],u=this._characterJoinerService.getJoinedCharacters(t),p=this._themeService.colors,_=e.getNoBgTrimmedLength();s&&_<n+1&&(_=n+1);let f,g=0,v="",m=0,y=0,b=0,w=0,S=!1,x=0,$=!1,k=0,C=0,E=[],R=-1!==h&&-1!==c;for(let P=0;P<_;P++){e.loadCell(P,this._workCell);let _=this._workCell.getWidth();if(0===_)continue;let A=!1,T=P>=C,D=P,L=this._workCell;if(u.length>0&&P===u[0][0]&&T){let i=u.shift(),r=this._isCellInSelection(i[0],t);for(m=i[0]+1;m<i[1];m++)T&&=r===this._isCellInSelection(m,t);T&&=!s||n<i[0]||n>=i[1],T?(A=!0,L=new ea(this._workCell,e.translateToString(!0,i[0],i[1]),i[1]-i[0]),D=i[1]-1,_=L.getWidth()):C=i[1]}let M=this._isCellInSelection(P,t),B=s&&P===n,O=R&&P>=h&&P<=c,z=!1;this._decorationService.forEachDecorationAtCell(P,t,void 0,e=>{z=!0});let I=L.getChars()||Ki;if(" "===I&&(L.isUnderline()||L.isOverline())&&(I=" "),k=_*a-l.get(I,L.isBold(),L.isItalic()),f){if(g&&(M&&$||!M&&!$&&L.bg===y)&&(M&&$&&p.selectionForeground||L.fg===b)&&L.extended.ext===w&&O===S&&k===x&&!B&&!A&&!z&&T){L.isInvisible()?v+=Ki:v+=I,g++;continue}g&&(f.textContent=v),f=this._document.createElement("span"),g=0,v=""}else f=this._document.createElement("span");if(y=L.bg,b=L.fg,w=L.extended.ext,S=O,x=k,$=M,A&&n>=P&&n<=D&&(n=P),!this._coreService.isCursorHidden&&B&&this._coreService.isCursorInitialized)if(E.push("xterm-cursor"),this._coreBrowserService.isFocused)o&&E.push("xterm-cursor-blink"),E.push("bar"===i?"xterm-cursor-bar":"underline"===i?"xterm-cursor-underline":"xterm-cursor-block");else if(r)switch(r){case"outline":E.push("xterm-cursor-outline");break;case"block":E.push("xterm-cursor-block");break;case"bar":E.push("xterm-cursor-bar");break;case"underline":E.push("xterm-cursor-underline")}if(L.isBold()&&E.push("xterm-bold"),L.isItalic()&&E.push("xterm-italic"),L.isDim()&&E.push("xterm-dim"),v=L.isInvisible()?Ki:L.getChars()||Ki,L.isUnderline()&&(E.push(`xterm-underline-${L.extended.underlineStyle}`)," "===v&&(v=" "),!L.isUnderlineColorDefault()))if(L.isUnderlineColorRGB())f.style.textDecorationColor=`rgb(${Vi.toColorRGB(L.getUnderlineColor()).join(",")})`;else{let e=L.getUnderlineColor();this._optionsService.rawOptions.drawBoldTextInBrightColors&&L.isBold()&&e<8&&(e+=8),f.style.textDecorationColor=p.ansi[e].css}L.isOverline()&&(E.push("xterm-overline")," "===v&&(v=" ")),L.isStrikethrough()&&E.push("xterm-strikethrough"),O&&(f.style.textDecoration="underline");let N=L.getFgColor(),F=L.getFgColorMode(),H=L.getBgColor(),W=L.getBgColorMode(),U=!!L.isInverse();if(U){let e=N;N=H,H=e;let t=F;F=W,W=t}let K,V,j,q=!1;switch(this._decorationService.forEachDecorationAtCell(P,t,void 0,e=>{"top"!==e.options.layer&&q||(e.backgroundColorRGB&&(W=50331648,H=e.backgroundColorRGB.rgba>>8&16777215,K=e.backgroundColorRGB),e.foregroundColorRGB&&(F=50331648,N=e.foregroundColorRGB.rgba>>8&16777215,V=e.foregroundColorRGB),q="top"===e.options.layer)}),!q&&M&&(K=this._coreBrowserService.isFocused?p.selectionBackgroundOpaque:p.selectionInactiveBackgroundOpaque,H=K.rgba>>8&16777215,W=50331648,q=!0,p.selectionForeground&&(F=50331648,N=p.selectionForeground.rgba>>8&16777215,V=p.selectionForeground)),q&&E.push("xterm-decoration-top"),W){case 16777216:case 33554432:j=p.ansi[H],E.push(`xterm-bg-${H}`);break;case 50331648:j=Wo.toColor(H>>16,H>>8&255,255&H),this._addStyle(f,`background-color:#${ia((H>>>0).toString(16),"0",6)}`);break;default:U?(j=p.foreground,E.push("xterm-bg-257")):j=p.background}switch(K||L.isDim()&&(K=Uo.multiplyOpacity(j,.5)),F){case 16777216:case 33554432:L.isBold()&&N<8&&this._optionsService.rawOptions.drawBoldTextInBrightColors&&(N+=8),this._applyMinimumContrast(f,j,p.ansi[N],L,K,void 0)||E.push(`xterm-fg-${N}`);break;case 50331648:let e=Wo.toColor(N>>16&255,N>>8&255,255&N);this._applyMinimumContrast(f,j,e,L,K,V)||this._addStyle(f,`color:#${ia(N.toString(16),"0",6)}`);break;default:this._applyMinimumContrast(f,j,p.foreground,L,K,V)||U&&E.push("xterm-fg-257")}E.length&&(f.className=E.join(" "),E.length=0),B||A||z||!T?f.textContent=v:g++,k!==this.defaultSpacing&&(f.style.letterSpacing=`${k}px`),d.push(f),P=D}return f&&g&&(f.textContent=v),d}_applyMinimumContrast(e,t,s,i,r,n){if(1===this._optionsService.rawOptions.minimumContrastRatio||function(e){return function(e){return 57508<=e&&e<=57558}(e)||function(e){return 9472<=e&&e<=9631}(e)}(i.getCode()))return!1;let o,a=this._getContrastCache(i);if(!r&&!n&&(o=a.getColor(t.rgba,s.rgba)),void 0===o){let e=this._optionsService.rawOptions.minimumContrastRatio/(i.isDim()?2:1);o=Uo.ensureContrastRatio(r||t,n||s,e),a.setColor((r||t).rgba,(n||s).rgba,o??null)}return!!o&&(this._addStyle(e,`color:${o.css}`),!0)}_getContrastCache(e){return e.isDim()?this._themeService.colors.halfContrastCache:this._themeService.colors.contrastCache}_addStyle(e,t){e.setAttribute("style",`${e.getAttribute("style")||""}${t};`)}_isCellInSelection(e,t){let s=this._selectionStart,i=this._selectionEnd;return!(!s||!i)&&(this._columnSelectMode?s[0]<=i[0]?e>=s[0]&&t>=s[1]&&e<i[0]&&t<=i[1]:e<s[0]&&t>=s[1]&&e>=i[0]&&t<=i[1]:t>s[1]&&t<i[1]||s[1]===i[1]&&t===s[1]&&e>=s[0]&&e<i[0]||s[1]<i[1]&&t===i[1]&&e<i[0]||s[1]<i[1]&&t===s[1]&&e>=s[0])}};function ia(e,t,s){for(;e.length<s;)e=t+e;return e}sa=Pi([Ai(1,fr),Ai(2,rr),Ai(3,dr),Ai(4,er),Ai(5,ar),Ai(6,gr)],sa);var ra=class{constructor(e,t){this._flat=new Float32Array(256),this._font="",this._fontSize=0,this._weight="normal",this._weightBold="bold",this._measureElements=[],this._container=e.createElement("div"),this._container.classList.add("xterm-width-cache-measure-container"),this._container.setAttribute("aria-hidden","true"),this._container.style.whiteSpace="pre",this._container.style.fontKerning="none";let s=e.createElement("span");s.classList.add("xterm-char-measure-element");let i=e.createElement("span");i.classList.add("xterm-char-measure-element"),i.style.fontWeight="bold";let r=e.createElement("span");r.classList.add("xterm-char-measure-element"),r.style.fontStyle="italic";let n=e.createElement("span");n.classList.add("xterm-char-measure-element"),n.style.fontWeight="bold",n.style.fontStyle="italic",this._measureElements=[s,i,r,n],this._container.appendChild(s),this._container.appendChild(i),this._container.appendChild(r),this._container.appendChild(n),t.appendChild(this._container),this.clear()}dispose(){this._container.remove(),this._measureElements.length=0,this._holey=void 0}clear(){this._flat.fill(-9999),this._holey=new Map}setFont(e,t,s,i){e===this._font&&t===this._fontSize&&s===this._weight&&i===this._weightBold||(this._font=e,this._fontSize=t,this._weight=s,this._weightBold=i,this._container.style.fontFamily=this._font,this._container.style.fontSize=`${this._fontSize}px`,this._measureElements[0].style.fontWeight=`${s}`,this._measureElements[1].style.fontWeight=`${i}`,this._measureElements[2].style.fontWeight=`${s}`,this._measureElements[3].style.fontWeight=`${i}`,this.clear())}get(e,t,s){let i=0;if(!t&&!s&&1===e.length&&(i=e.charCodeAt(0))<256){if(-9999!==this._flat[i])return this._flat[i];let t=this._measure(e,0);return t>0&&(this._flat[i]=t),t}let r=e;t&&(r+="B"),s&&(r+="I");let n=this._holey.get(r);if(void 0===n){let i=0;t&&(i|=1),s&&(i|=2),n=this._measure(e,i),n>0&&this._holey.set(r,n)}return n}_measure(e,t){let s=this._measureElements[t];return s.textContent=e.repeat(32),s.offsetWidth/32}},na=class{constructor(){this.clear()}clear(){this.hasSelection=!1,this.columnSelectMode=!1,this.viewportStartRow=0,this.viewportEndRow=0,this.viewportCappedStartRow=0,this.viewportCappedEndRow=0,this.startCol=0,this.endCol=0,this.selectionStart=void 0,this.selectionEnd=void 0}update(e,t,s,i=!1){if(this.selectionStart=t,this.selectionEnd=s,!t||!s||t[0]===s[0]&&t[1]===s[1])return void this.clear();let r=e.buffers.active.ydisp,n=t[1]-r,o=s[1]-r,a=Math.max(n,0),l=Math.min(o,e.rows-1);a>=e.rows||l<0?this.clear():(this.hasSelection=!0,this.columnSelectMode=i,this.viewportStartRow=n,this.viewportEndRow=o,this.viewportCappedStartRow=a,this.viewportCappedEndRow=l,this.startCol=t[0],this.endCol=s[0])}isCellSelected(e,t,s){return!!this.hasSelection&&(s-=e.buffer.active.viewportY,this.columnSelectMode?this.startCol<=this.endCol?t>=this.startCol&&s>=this.viewportCappedStartRow&&t<this.endCol&&s<=this.viewportCappedEndRow:t<this.startCol&&s>=this.viewportCappedStartRow&&t>=this.endCol&&s<=this.viewportCappedEndRow:s>this.viewportStartRow&&s<this.viewportEndRow||this.viewportStartRow===this.viewportEndRow&&s===this.viewportStartRow&&t>=this.startCol&&t<this.endCol||this.viewportStartRow<this.viewportEndRow&&s===this.viewportEndRow&&t<this.endCol||this.viewportStartRow<this.viewportEndRow&&s===this.viewportStartRow&&t>=this.startCol)}};var oa="xterm-dom-renderer-owner-",aa="xterm-rows",la="xterm-fg-",ha="xterm-bg-",ca="xterm-focus",da="xterm-selection",ua=1,pa=class extends Dr{constructor(e,t,s,i,r,n,o,a,l,h,c,d,u,p){super(),this._terminal=e,this._document=t,this._element=s,this._screenElement=i,this._viewportElement=r,this._helperContainer=n,this._linkifier2=o,this._charSizeService=l,this._optionsService=h,this._bufferService=c,this._coreService=d,this._coreBrowserService=u,this._themeService=p,this._terminalClass=ua++,this._rowElements=[],this._selectionRenderModel=new na,this.onRequestRedraw=this._register(new Xr).event,this._rowContainer=this._document.createElement("div"),this._rowContainer.classList.add(aa),this._rowContainer.style.lineHeight="normal",this._rowContainer.setAttribute("aria-hidden","true"),this._refreshRowElements(this._bufferService.cols,this._bufferService.rows),this._selectionContainer=this._document.createElement("div"),this._selectionContainer.classList.add(da),this._selectionContainer.setAttribute("aria-hidden","true"),this.dimensions={css:{canvas:{width:0,height:0},cell:{width:0,height:0}},device:{canvas:{width:0,height:0},cell:{width:0,height:0},char:{width:0,height:0,left:0,top:0}}},this._updateDimensions(),this._register(this._optionsService.onOptionChange(()=>this._handleOptionsChanged())),this._register(this._themeService.onChangeColors(e=>this._injectCss(e))),this._injectCss(this._themeService.colors),this._rowFactory=a.createInstance(sa,document),this._element.classList.add(oa+this._terminalClass),this._screenElement.appendChild(this._rowContainer),this._screenElement.appendChild(this._selectionContainer),this._register(this._linkifier2.onShowLinkUnderline(e=>this._handleLinkHover(e))),this._register(this._linkifier2.onHideLinkUnderline(e=>this._handleLinkLeave(e))),this._register(Pr(()=>{this._element.classList.remove(oa+this._terminalClass),this._rowContainer.remove(),this._selectionContainer.remove(),this._widthCache.dispose(),this._themeStyleElement.remove(),this._dimensionsStyleElement.remove()})),this._widthCache=new ra(this._document,this._helperContainer),this._widthCache.setFont(this._optionsService.rawOptions.fontFamily,this._optionsService.rawOptions.fontSize,this._optionsService.rawOptions.fontWeight,this._optionsService.rawOptions.fontWeightBold),this._setDefaultSpacing()}_updateDimensions(){let e=this._coreBrowserService.dpr;this.dimensions.device.char.width=this._charSizeService.width*e,this.dimensions.device.char.height=Math.ceil(this._charSizeService.height*e),this.dimensions.device.cell.width=this.dimensions.device.char.width+Math.round(this._optionsService.rawOptions.letterSpacing),this.dimensions.device.cell.height=Math.floor(this.dimensions.device.char.height*this._optionsService.rawOptions.lineHeight),this.dimensions.device.char.left=0,this.dimensions.device.char.top=0,this.dimensions.device.canvas.width=this.dimensions.device.cell.width*this._bufferService.cols,this.dimensions.device.canvas.height=this.dimensions.device.cell.height*this._bufferService.rows,this.dimensions.css.canvas.width=Math.round(this.dimensions.device.canvas.width/e),this.dimensions.css.canvas.height=Math.round(this.dimensions.device.canvas.height/e),this.dimensions.css.cell.width=this.dimensions.css.canvas.width/this._bufferService.cols,this.dimensions.css.cell.height=this.dimensions.css.canvas.height/this._bufferService.rows;for(let e of this._rowElements)e.style.width=`${this.dimensions.css.canvas.width}px`,e.style.height=`${this.dimensions.css.cell.height}px`,e.style.lineHeight=`${this.dimensions.css.cell.height}px`,e.style.overflow="hidden";this._dimensionsStyleElement||(this._dimensionsStyleElement=this._document.createElement("style"),this._screenElement.appendChild(this._dimensionsStyleElement));let t=`${this._terminalSelector} .${aa} span { display: inline-block; height: 100%; vertical-align: top;}`;this._dimensionsStyleElement.textContent=t,this._selectionContainer.style.height=this._viewportElement.style.height,this._screenElement.style.width=`${this.dimensions.css.canvas.width}px`,this._screenElement.style.height=`${this.dimensions.css.canvas.height}px`}_injectCss(e){this._themeStyleElement||(this._themeStyleElement=this._document.createElement("style"),this._screenElement.appendChild(this._themeStyleElement));let t=`${this._terminalSelector} .${aa} { pointer-events: none; color: ${e.foreground.css}; font-family: ${this._optionsService.rawOptions.fontFamily}; font-size: ${this._optionsService.rawOptions.fontSize}px; font-kerning: none; white-space: pre}`;t+=`${this._terminalSelector} .${aa} .xterm-dim { color: ${Uo.multiplyOpacity(e.foreground,.5).css};}`,t+=`${this._terminalSelector} span:not(.xterm-bold) { font-weight: ${this._optionsService.rawOptions.fontWeight};}${this._terminalSelector} span.xterm-bold { font-weight: ${this._optionsService.rawOptions.fontWeightBold};}${this._terminalSelector} span.xterm-italic { font-style: italic;}`;let s=`blink_underline_${this._terminalClass}`,i=`blink_bar_${this._terminalClass}`,r=`blink_block_${this._terminalClass}`;t+=`@keyframes ${s} { 50% {  border-bottom-style: hidden; }}`,t+=`@keyframes ${i} { 50% {  box-shadow: none; }}`,t+=`@keyframes ${r} { 0% {  background-color: ${e.cursor.css};  color: ${e.cursorAccent.css}; } 50% {  background-color: inherit;  color: ${e.cursor.css}; }}`,t+=`${this._terminalSelector} .${aa}.${ca} .xterm-cursor.xterm-cursor-blink.xterm-cursor-underline { animation: ${s} 1s step-end infinite;}${this._terminalSelector} .${aa}.${ca} .xterm-cursor.xterm-cursor-blink.xterm-cursor-bar { animation: ${i} 1s step-end infinite;}${this._terminalSelector} .${aa}.${ca} .xterm-cursor.xterm-cursor-blink.xterm-cursor-block { animation: ${r} 1s step-end infinite;}${this._terminalSelector} .${aa} .xterm-cursor.xterm-cursor-block { background-color: ${e.cursor.css}; color: ${e.cursorAccent.css};}${this._terminalSelector} .${aa} .xterm-cursor.xterm-cursor-block:not(.xterm-cursor-blink) { background-color: ${e.cursor.css} !important; color: ${e.cursorAccent.css} !important;}${this._terminalSelector} .${aa} .xterm-cursor.xterm-cursor-outline { outline: 1px solid ${e.cursor.css}; outline-offset: -1px;}${this._terminalSelector} .${aa} .xterm-cursor.xterm-cursor-bar { box-shadow: ${this._optionsService.rawOptions.cursorWidth}px 0 0 ${e.cursor.css} inset;}${this._terminalSelector} .${aa} .xterm-cursor.xterm-cursor-underline { border-bottom: 1px ${e.cursor.css}; border-bottom-style: solid; height: calc(100% - 1px);}`,t+=`${this._terminalSelector} .${da} { position: absolute; top: 0; left: 0; z-index: 1; pointer-events: none;}${this._terminalSelector}.focus .${da} div { position: absolute; background-color: ${e.selectionBackgroundOpaque.css};}${this._terminalSelector} .${da} div { position: absolute; background-color: ${e.selectionInactiveBackgroundOpaque.css};}`;for(let[s,i]of e.ansi.entries())t+=`${this._terminalSelector} .${la}${s} { color: ${i.css}; }${this._terminalSelector} .${la}${s}.xterm-dim { color: ${Uo.multiplyOpacity(i,.5).css}; }${this._terminalSelector} .${ha}${s} { background-color: ${i.css}; }`;t+=`${this._terminalSelector} .${la}257 { color: ${Uo.opaque(e.background).css}; }${this._terminalSelector} .${la}257.xterm-dim { color: ${Uo.multiplyOpacity(Uo.opaque(e.background),.5).css}; }${this._terminalSelector} .${ha}257 { background-color: ${e.foreground.css}; }`,this._themeStyleElement.textContent=t}_setDefaultSpacing(){let e=this.dimensions.css.cell.width-this._widthCache.get("W",!1,!1);this._rowContainer.style.letterSpacing=`${e}px`,this._rowFactory.defaultSpacing=e}handleDevicePixelRatioChange(){this._updateDimensions(),this._widthCache.clear(),this._setDefaultSpacing()}_refreshRowElements(e,t){for(let e=this._rowElements.length;e<=t;e++){let e=this._document.createElement("div");this._rowContainer.appendChild(e),this._rowElements.push(e)}for(;this._rowElements.length>t;)this._rowContainer.removeChild(this._rowElements.pop())}handleResize(e,t){this._refreshRowElements(e,t),this._updateDimensions(),this.handleSelectionChanged(this._selectionRenderModel.selectionStart,this._selectionRenderModel.selectionEnd,this._selectionRenderModel.columnSelectMode)}handleCharSizeChanged(){this._updateDimensions(),this._widthCache.clear(),this._setDefaultSpacing()}handleBlur(){this._rowContainer.classList.remove(ca),this.renderRows(0,this._bufferService.rows-1)}handleFocus(){this._rowContainer.classList.add(ca),this.renderRows(this._bufferService.buffer.y,this._bufferService.buffer.y)}handleSelectionChanged(e,t,s){if(this._selectionContainer.replaceChildren(),this._rowFactory.handleSelectionChanged(e,t,s),this.renderRows(0,this._bufferService.rows-1),!e||!t||(this._selectionRenderModel.update(this._terminal,e,t,s),!this._selectionRenderModel.hasSelection))return;let i=this._selectionRenderModel.viewportStartRow,r=this._selectionRenderModel.viewportEndRow,n=this._selectionRenderModel.viewportCappedStartRow,o=this._selectionRenderModel.viewportCappedEndRow,a=this._document.createDocumentFragment();if(s){let s=e[0]>t[0];a.appendChild(this._createSelectionElement(n,s?t[0]:e[0],s?e[0]:t[0],o-n+1))}else{let s=i===n?e[0]:0,l=n===r?t[0]:this._bufferService.cols;a.appendChild(this._createSelectionElement(n,s,l));let h=o-n-1;if(a.appendChild(this._createSelectionElement(n+1,0,this._bufferService.cols,h)),n!==o){let e=r===o?t[0]:this._bufferService.cols;a.appendChild(this._createSelectionElement(o,0,e))}}this._selectionContainer.appendChild(a)}_createSelectionElement(e,t,s,i=1){let r=this._document.createElement("div"),n=t*this.dimensions.css.cell.width,o=this.dimensions.css.cell.width*(s-t);return n+o>this.dimensions.css.canvas.width&&(o=this.dimensions.css.canvas.width-n),r.style.height=i*this.dimensions.css.cell.height+"px",r.style.top=e*this.dimensions.css.cell.height+"px",r.style.left=`${n}px`,r.style.width=`${o}px`,r}handleCursorMove(){}_handleOptionsChanged(){this._updateDimensions(),this._injectCss(this._themeService.colors),this._widthCache.setFont(this._optionsService.rawOptions.fontFamily,this._optionsService.rawOptions.fontSize,this._optionsService.rawOptions.fontWeight,this._optionsService.rawOptions.fontWeightBold),this._setDefaultSpacing()}clear(){for(let e of this._rowElements)e.replaceChildren()}renderRows(e,t){let s=this._bufferService.buffer,i=s.ybase+s.y,r=Math.min(s.x,this._bufferService.cols-1),n=this._coreService.decPrivateModes.cursorBlink??this._optionsService.rawOptions.cursorBlink,o=this._coreService.decPrivateModes.cursorStyle??this._optionsService.rawOptions.cursorStyle,a=this._optionsService.rawOptions.cursorInactiveStyle;for(let l=e;l<=t;l++){let e=l+s.ydisp,t=this._rowElements[l],h=s.lines.get(e);if(!t||!h)break;t.replaceChildren(...this._rowFactory.createRow(h,e,e===i,o,a,r,n,this.dimensions.css.cell.width,this._widthCache,-1,-1))}}get _terminalSelector(){return`.${oa}${this._terminalClass}`}_handleLinkHover(e){this._setCellUnderline(e.x1,e.x2,e.y1,e.y2,e.cols,!0)}_handleLinkLeave(e){this._setCellUnderline(e.x1,e.x2,e.y1,e.y2,e.cols,!1)}_setCellUnderline(e,t,s,i,r,n){s<0&&(e=0),i<0&&(t=0);let o=this._bufferService.rows-1;s=Math.max(Math.min(s,o),0),i=Math.max(Math.min(i,o),0),r=Math.min(r,this._bufferService.cols);let a=this._bufferService.buffer,l=a.ybase+a.y,h=Math.min(a.x,r-1),c=this._optionsService.rawOptions.cursorBlink,d=this._optionsService.rawOptions.cursorStyle,u=this._optionsService.rawOptions.cursorInactiveStyle;for(let o=s;o<=i;++o){let p=o+a.ydisp,_=this._rowElements[o],f=a.lines.get(p);if(!_||!f)break;_.replaceChildren(...this._rowFactory.createRow(f,p,p===l,d,u,h,c,this.dimensions.css.cell.width,this._widthCache,n?o===s?e:0:-1,n?(o===i?t:r)-1:-1))}}};pa=Pi([Ai(7,sr),Ai(8,cr),Ai(9,rr),Ai(10,Zi),Ai(11,er),Ai(12,dr),Ai(13,gr)],pa);var _a=class extends Dr{constructor(e,t,s){super(),this._optionsService=s,this.width=0,this.height=0,this._onCharSizeChange=this._register(new Xr),this.onCharSizeChange=this._onCharSizeChange.event;try{this._measureStrategy=this._register(new va(this._optionsService))}catch{this._measureStrategy=this._register(new ga(e,t,this._optionsService))}this._register(this._optionsService.onMultipleOptionChange(["fontFamily","fontSize"],()=>this.measure()))}get hasValidSize(){return this.width>0&&this.height>0}measure(){let e=this._measureStrategy.measure();(e.width!==this.width||e.height!==this.height)&&(this.width=e.width,this.height=e.height,this._onCharSizeChange.fire())}};_a=Pi([Ai(2,rr)],_a);var fa=class extends Dr{constructor(){super(...arguments),this._result={width:0,height:0}}_validateAndSet(e,t){void 0!==e&&e>0&&void 0!==t&&t>0&&(this._result.width=e,this._result.height=t)}},ga=class extends fa{constructor(e,t,s){super(),this._document=e,this._parentElement=t,this._optionsService=s,this._measureElement=this._document.createElement("span"),this._measureElement.classList.add("xterm-char-measure-element"),this._measureElement.textContent="W".repeat(32),this._measureElement.setAttribute("aria-hidden","true"),this._measureElement.style.whiteSpace="pre",this._measureElement.style.fontKerning="none",this._parentElement.appendChild(this._measureElement)}measure(){return this._measureElement.style.fontFamily=this._optionsService.rawOptions.fontFamily,this._measureElement.style.fontSize=`${this._optionsService.rawOptions.fontSize}px`,this._validateAndSet(Number(this._measureElement.offsetWidth)/32,Number(this._measureElement.offsetHeight)),this._result}},va=class extends fa{constructor(e){super(),this._optionsService=e,this._canvas=new OffscreenCanvas(100,100),this._ctx=this._canvas.getContext("2d");let t=this._ctx.measureText("W");if(!("width"in t&&"fontBoundingBoxAscent"in t&&"fontBoundingBoxDescent"in t))throw new Error("Required font metrics not supported")}measure(){this._ctx.font=`${this._optionsService.rawOptions.fontSize}px ${this._optionsService.rawOptions.fontFamily}`;let e=this._ctx.measureText("W");return this._validateAndSet(e.width,e.fontBoundingBoxAscent+e.fontBoundingBoxDescent),this._result}},ma=class extends Dr{constructor(e,t,s){super(),this._textarea=e,this._window=t,this.mainDocument=s,this._isFocused=!1,this._cachedIsFocused=void 0,this._screenDprMonitor=this._register(new ya(this._window)),this._onDprChange=this._register(new Xr),this.onDprChange=this._onDprChange.event,this._onWindowChange=this._register(new Xr),this.onWindowChange=this._onWindowChange.event,this._register(this.onWindowChange(e=>this._screenDprMonitor.setWindow(e))),this._register(Or.forward(this._screenDprMonitor.onDprChange,this._onDprChange)),this._register(eo(this._textarea,"focus",()=>this._isFocused=!0)),this._register(eo(this._textarea,"blur",()=>this._isFocused=!1))}get window(){return this._window}set window(e){this._window!==e&&(this._window=e,this._onWindowChange.fire(this._window))}get dpr(){return this.window.devicePixelRatio}get isFocused(){return void 0===this._cachedIsFocused&&(this._cachedIsFocused=this._isFocused&&this._textarea.ownerDocument.hasFocus(),queueMicrotask(()=>this._cachedIsFocused=void 0)),this._cachedIsFocused}},ya=class extends Dr{constructor(e){super(),this._parentWindow=e,this._windowResizeListener=this._register(new Lr),this._onDprChange=this._register(new Xr),this.onDprChange=this._onDprChange.event,this._outerListener=()=>this._setDprAndFireIfDiffers(),this._currentDevicePixelRatio=this._parentWindow.devicePixelRatio,this._updateDpr(),this._setWindowResizeListener(),this._register(Pr(()=>this.clearListener()))}setWindow(e){this._parentWindow=e,this._setWindowResizeListener(),this._setDprAndFireIfDiffers()}_setWindowResizeListener(){this._windowResizeListener.value=eo(this._parentWindow,"resize",()=>this._setDprAndFireIfDiffers())}_setDprAndFireIfDiffers(){this._parentWindow.devicePixelRatio!==this._currentDevicePixelRatio&&this._onDprChange.fire(this._parentWindow.devicePixelRatio),this._updateDpr()}_updateDpr(){this._outerListener&&(this._resolutionMediaMatchList?.removeListener(this._outerListener),this._currentDevicePixelRatio=this._parentWindow.devicePixelRatio,this._resolutionMediaMatchList=this._parentWindow.matchMedia(`screen and (resolution: ${this._parentWindow.devicePixelRatio}dppx)`),this._resolutionMediaMatchList.addListener(this._outerListener))}clearListener(){!this._resolutionMediaMatchList||!this._outerListener||(this._resolutionMediaMatchList.removeListener(this._outerListener),this._resolutionMediaMatchList=void 0,this._outerListener=void 0)}},ba=class extends Dr{constructor(){super(),this.linkProviders=[],this._register(Pr(()=>this.linkProviders.length=0))}registerLinkProvider(e){return this.linkProviders.push(e),{dispose:()=>{let t=this.linkProviders.indexOf(e);-1!==t&&this.linkProviders.splice(t,1)}}}};function wa(e,t,s){let i=s.getBoundingClientRect(),r=e.getComputedStyle(s),n=parseInt(r.getPropertyValue("padding-left")),o=parseInt(r.getPropertyValue("padding-top"));return[t.clientX-i.left-n,t.clientY-i.top-o]}var Sa=class{constructor(e,t){this._renderService=e,this._charSizeService=t}getCoords(e,t,s,i,r){return function(e,t,s,i,r,n,o,a,l){if(!n)return;let h=wa(e,t,s);return h?(h[0]=Math.ceil((h[0]+(l?o/2:0))/o),h[1]=Math.ceil(h[1]/a),h[0]=Math.min(Math.max(h[0],1),i+(l?1:0)),h[1]=Math.min(Math.max(h[1],1),r),h):void 0}(window,e,t,s,i,this._charSizeService.hasValidSize,this._renderService.dimensions.css.cell.width,this._renderService.dimensions.css.cell.height,r)}getMouseReportCoords(e,t){let s=wa(window,e,t);if(this._charSizeService.hasValidSize)return s[0]=Math.min(Math.max(s[0],0),this._renderService.dimensions.css.canvas.width-1),s[1]=Math.min(Math.max(s[1],0),this._renderService.dimensions.css.canvas.height-1),{col:Math.floor(s[0]/this._renderService.dimensions.css.cell.width),row:Math.floor(s[1]/this._renderService.dimensions.css.cell.height),x:Math.floor(s[0]),y:Math.floor(s[1])}}};Sa=Pi([Ai(0,pr),Ai(1,cr)],Sa);var xa=class{constructor(e,t){this._renderCallback=e,this._coreBrowserService=t,this._refreshCallbacks=[]}dispose(){this._animationFrame&&(this._coreBrowserService.window.cancelAnimationFrame(this._animationFrame),this._animationFrame=void 0)}addRefreshCallback(e){return this._refreshCallbacks.push(e),this._animationFrame||(this._animationFrame=this._coreBrowserService.window.requestAnimationFrame(()=>this._innerRefresh())),this._animationFrame}refresh(e,t,s){this._rowCount=s,e=void 0!==e?e:0,t=void 0!==t?t:this._rowCount-1,this._rowStart=void 0!==this._rowStart?Math.min(this._rowStart,e):e,this._rowEnd=void 0!==this._rowEnd?Math.max(this._rowEnd,t):t,!this._animationFrame&&(this._animationFrame=this._coreBrowserService.window.requestAnimationFrame(()=>this._innerRefresh()))}_innerRefresh(){if(this._animationFrame=void 0,void 0===this._rowStart||void 0===this._rowEnd||void 0===this._rowCount)return void this._runRefreshCallbacks();let e=Math.max(this._rowStart,0),t=Math.min(this._rowEnd,this._rowCount-1);this._rowStart=void 0,this._rowEnd=void 0,this._renderCallback(e,t),this._runRefreshCallbacks()}_runRefreshCallbacks(){for(let e of this._refreshCallbacks)e(0);this._refreshCallbacks=[]}},$a={};((e,t)=>{for(var s in t)Ei(e,s,{get:t[s],enumerable:!0})})($a,{getSafariVersion:()=>Ta,isChromeOS:()=>za,isFirefox:()=>Ra,isIpad:()=>La,isIphone:()=>Ma,isLegacyEdge:()=>Pa,isLinux:()=>Oa,isMac:()=>Da,isNode:()=>ka,isSafari:()=>Aa,isWindows:()=>Ba});var ka=typeof process<"u"&&"title"in process,Ca=ka?"node":navigator.userAgent,Ea=ka?"node":navigator.platform,Ra=Ca.includes("Firefox"),Pa=Ca.includes("Edge"),Aa=/^((?!chrome|android).)*safari/i.test(Ca);function Ta(){if(!Aa)return 0;let e=Ca.match(/Version\/(\d+)/);return null===e||e.length<2?0:parseInt(e[1])}var Da=["Macintosh","MacIntel","MacPPC","Mac68K"].includes(Ea),La="iPad"===Ea,Ma="iPhone"===Ea,Ba=["Windows","Win16","Win32","WinCE"].includes(Ea),Oa=Ea.indexOf("Linux")>=0,za=/\bCrOS\b/.test(Ca),Ia=class{constructor(){this._tasks=[],this._i=0}enqueue(e){this._tasks.push(e),this._start()}flush(){for(;this._i<this._tasks.length;)this._tasks[this._i]()||this._i++;this.clear()}clear(){this._idleCallback&&(this._cancelCallback(this._idleCallback),this._idleCallback=void 0),this._i=0,this._tasks.length=0}_start(){this._idleCallback||(this._idleCallback=this._requestCallback(this._process.bind(this)))}_process(e){this._idleCallback=void 0;let t=0,s=0,i=e.timeRemaining(),r=0;for(;this._i<this._tasks.length;){if(t=performance.now(),this._tasks[this._i]()||this._i++,t=Math.max(1,performance.now()-t),s=Math.max(t,s),r=e.timeRemaining(),1.5*s>r)return i-t<-20&&console.warn(`task queue exceeded allotted deadline by ${Math.abs(Math.round(i-t))}ms`),void this._start();i=r}this.clear()}},Na=!ka&&"requestIdleCallback"in window?class extends Ia{_requestCallback(e){return requestIdleCallback(e)}_cancelCallback(e){cancelIdleCallback(e)}}:class extends Ia{_requestCallback(e){return setTimeout(()=>e(this._createDeadline(16)))}_cancelCallback(e){clearTimeout(e)}_createDeadline(e){let t=performance.now()+e;return{timeRemaining:()=>Math.max(0,t-performance.now())}}},Fa=class{constructor(){this._queue=new Na}set(e){this._queue.clear(),this._queue.enqueue(e)}flush(){this._queue.flush()}},Ha=class extends Dr{constructor(e,t,s,i,r,n,o,a,l){super(),this._rowCount=e,this._optionsService=s,this._charSizeService=i,this._coreService=r,this._coreBrowserService=a,this._renderer=this._register(new Lr),this._pausedResizeTask=new Fa,this._observerDisposable=this._register(new Lr),this._isPaused=!1,this._needsFullRefresh=!1,this._isNextRenderRedrawOnly=!0,this._needsSelectionRefresh=!1,this._canvasWidth=0,this._canvasHeight=0,this._selectionState={start:void 0,end:void 0,columnSelectMode:!1},this._onDimensionsChange=this._register(new Xr),this.onDimensionsChange=this._onDimensionsChange.event,this._onRenderedViewportChange=this._register(new Xr),this.onRenderedViewportChange=this._onRenderedViewportChange.event,this._onRender=this._register(new Xr),this.onRender=this._onRender.event,this._onRefreshRequest=this._register(new Xr),this.onRefreshRequest=this._onRefreshRequest.event,this._renderDebouncer=new xa((e,t)=>this._renderRows(e,t),this._coreBrowserService),this._register(this._renderDebouncer),this._syncOutputHandler=new Wa(this._coreBrowserService,this._coreService,()=>this._fullRefresh()),this._register(Pr(()=>this._syncOutputHandler.dispose())),this._register(this._coreBrowserService.onDprChange(()=>this.handleDevicePixelRatioChange())),this._register(o.onResize(()=>this._fullRefresh())),this._register(o.buffers.onBufferActivate(()=>this._renderer.value?.clear())),this._register(this._optionsService.onOptionChange(()=>this._handleOptionsChanged())),this._register(this._charSizeService.onCharSizeChange(()=>this.handleCharSizeChanged())),this._register(n.onDecorationRegistered(()=>this._fullRefresh())),this._register(n.onDecorationRemoved(()=>this._fullRefresh())),this._register(this._optionsService.onMultipleOptionChange(["customGlyphs","drawBoldTextInBrightColors","letterSpacing","lineHeight","fontFamily","fontSize","fontWeight","fontWeightBold","minimumContrastRatio","rescaleOverlappingGlyphs"],()=>{this.clear(),this.handleResize(o.cols,o.rows),this._fullRefresh()})),this._register(this._optionsService.onMultipleOptionChange(["cursorBlink","cursorStyle"],()=>this.refreshRows(o.buffer.y,o.buffer.y,!0))),this._register(l.onChangeColors(()=>this._fullRefresh())),this._registerIntersectionObserver(this._coreBrowserService.window,t),this._register(this._coreBrowserService.onWindowChange(e=>this._registerIntersectionObserver(e,t)))}get dimensions(){return this._renderer.value.dimensions}_registerIntersectionObserver(e,t){if("IntersectionObserver"in e){let s=new e.IntersectionObserver(e=>this._handleIntersectionChange(e[e.length-1]),{threshold:0});s.observe(t),this._observerDisposable.value=Pr(()=>s.disconnect())}}_handleIntersectionChange(e){this._isPaused=void 0===e.isIntersecting?0===e.intersectionRatio:!e.isIntersecting,!this._isPaused&&!this._charSizeService.hasValidSize&&this._charSizeService.measure(),!this._isPaused&&this._needsFullRefresh&&(this._pausedResizeTask.flush(),this.refreshRows(0,this._rowCount-1),this._needsFullRefresh=!1)}refreshRows(e,t,s=!1){if(this._isPaused)return void(this._needsFullRefresh=!0);if(this._coreService.decPrivateModes.synchronizedOutput)return void this._syncOutputHandler.bufferRows(e,t);let i=this._syncOutputHandler.flush();i&&(e=Math.min(e,i.start),t=Math.max(t,i.end)),s||(this._isNextRenderRedrawOnly=!1),this._renderDebouncer.refresh(e,t,this._rowCount)}_renderRows(e,t){if(this._renderer.value){if(this._coreService.decPrivateModes.synchronizedOutput)return void this._syncOutputHandler.bufferRows(e,t);e=Math.min(e,this._rowCount-1),t=Math.min(t,this._rowCount-1),this._renderer.value.renderRows(e,t),this._needsSelectionRefresh&&(this._renderer.value.handleSelectionChanged(this._selectionState.start,this._selectionState.end,this._selectionState.columnSelectMode),this._needsSelectionRefresh=!1),this._isNextRenderRedrawOnly||this._onRenderedViewportChange.fire({start:e,end:t}),this._onRender.fire({start:e,end:t}),this._isNextRenderRedrawOnly=!0}}resize(e,t){this._rowCount=t,this._fireOnCanvasResize()}_handleOptionsChanged(){this._renderer.value&&(this.refreshRows(0,this._rowCount-1),this._fireOnCanvasResize())}_fireOnCanvasResize(){this._renderer.value&&(this._renderer.value.dimensions.css.canvas.width===this._canvasWidth&&this._renderer.value.dimensions.css.canvas.height===this._canvasHeight||this._onDimensionsChange.fire(this._renderer.value.dimensions))}hasRenderer(){return!!this._renderer.value}setRenderer(e){this._renderer.value=e,this._renderer.value&&(this._renderer.value.onRequestRedraw(e=>this.refreshRows(e.start,e.end,!0)),this._needsSelectionRefresh=!0,this._fullRefresh())}addRefreshCallback(e){return this._renderDebouncer.addRefreshCallback(e)}_fullRefresh(){this._isPaused?this._needsFullRefresh=!0:this.refreshRows(0,this._rowCount-1)}clearTextureAtlas(){this._renderer.value&&(this._renderer.value.clearTextureAtlas?.(),this._fullRefresh())}handleDevicePixelRatioChange(){this._charSizeService.measure(),this._renderer.value&&(this._renderer.value.handleDevicePixelRatioChange(),this.refreshRows(0,this._rowCount-1))}handleResize(e,t){this._renderer.value&&(this._isPaused?this._pausedResizeTask.set(()=>this._renderer.value?.handleResize(e,t)):this._renderer.value.handleResize(e,t),this._fullRefresh())}handleCharSizeChanged(){this._renderer.value?.handleCharSizeChanged()}handleBlur(){this._renderer.value?.handleBlur()}handleFocus(){this._renderer.value?.handleFocus()}handleSelectionChanged(e,t,s){this._selectionState.start=e,this._selectionState.end=t,this._selectionState.columnSelectMode=s,this._renderer.value?.handleSelectionChanged(e,t,s)}handleCursorMove(){this._renderer.value?.handleCursorMove()}clear(){this._renderer.value?.clear()}};Ha=Pi([Ai(2,rr),Ai(3,cr),Ai(4,er),Ai(5,ar),Ai(6,Zi),Ai(7,dr),Ai(8,gr)],Ha);var Wa=class{constructor(e,t,s){this._coreBrowserService=e,this._coreService=t,this._onTimeout=s,this._start=0,this._end=0,this._isBuffering=!1}bufferRows(e,t){this._isBuffering?(this._start=Math.min(this._start,e),this._end=Math.max(this._end,t)):(this._start=e,this._end=t,this._isBuffering=!0),void 0===this._timeout&&(this._timeout=this._coreBrowserService.window.setTimeout(()=>{this._timeout=void 0,this._coreService.decPrivateModes.synchronizedOutput=!1,this._onTimeout()},1e3))}flush(){if(void 0!==this._timeout&&(this._coreBrowserService.window.clearTimeout(this._timeout),this._timeout=void 0),!this._isBuffering)return;let e={start:this._start,end:this._end};return this._isBuffering=!1,e}dispose(){void 0!==this._timeout&&(this._coreBrowserService.window.clearTimeout(this._timeout),this._timeout=void 0)}};function Ua(e,t,s,i){let r,n=s.buffer.x,o=s.buffer.y;if(!s.buffer.hasScrollback)return function(e,t,s,i,r,n){return 0===Ka(t,i,r,n).length?"":Ga(qa(e,t,e,t-Va(t,r),!1,r).length,Ya("D",n))}(n,o,0,t,s,i)+Ka(o,t,s,i)+function(e,t,s,i,r,n){let o;o=Ka(t,i,r,n).length>0?i-Va(i,r):t;let a=i,l=function(e,t,s,i,r,n){let o;return o=Ka(s,i,r,n).length>0?i-Va(i,r):t,e<s&&o<=i||e>=s&&o<i?"C":"D"}(e,t,s,i,r,n);return Ga(qa(e,o,s,a,"C"===l,r).length,Ya(l,n))}(n,o,e,t,s,i);if(o===t)return r=n>e?"D":"C",Ga(Math.abs(n-e),Ya(r,i));r=o>t?"D":"C";let a=Math.abs(o-t),l=function(e,t){return t.cols-e}(o>t?e:n,s)+(a-1)*s.cols+1+function(e){return e-1}(o>t?n:e);return Ga(l,Ya(r,i))}function Ka(e,t,s,i){let r=e-Va(e,s),n=t-Va(t,s),o=Math.abs(r-n)-function(e,t,s){let i=0,r=e-Va(e,s),n=t-Va(t,s);for(let o=0;o<Math.abs(r-n);o++){let n="A"===ja(e,t)?-1:1;s.buffer.lines.get(r+n*o)?.isWrapped&&i++}return i}(e,t,s);return Ga(o,Ya(ja(e,t),i))}function Va(e,t){let s=0,i=t.buffer.lines.get(e),r=i?.isWrapped;for(;r&&e>=0&&e<t.rows;)s++,i=t.buffer.lines.get(--e),r=i?.isWrapped;return s}function ja(e,t){return e>t?"A":"B"}function qa(e,t,s,i,r,n){let o=e,a=t,l="";for(;(o!==s||a!==i)&&a>=0&&a<n.buffer.lines.length;)o+=r?1:-1,r&&o>n.cols-1?(l+=n.buffer.translateBufferLineToString(a,!1,e,o),o=0,e=0,a++):!r&&o<0&&(l+=n.buffer.translateBufferLineToString(a,!1,0,e+1),o=n.cols-1,e=o,a--);return l+n.buffer.translateBufferLineToString(a,!1,e,o)}function Ya(e,t){let s=t?"O":"[";return Lo.ESC+s+e}function Ga(e,t){e=Math.floor(e);let s="";for(let i=0;i<e;i++)s+=t;return s}var Xa=class{constructor(e){this._bufferService=e,this.isSelectAllActive=!1,this.selectionStartLength=0}clearSelection(){this.selectionStart=void 0,this.selectionEnd=void 0,this.isSelectAllActive=!1,this.selectionStartLength=0}get finalSelectionStart(){return this.isSelectAllActive?[0,0]:this.selectionEnd&&this.selectionStart&&this.areSelectionValuesReversed()?this.selectionEnd:this.selectionStart}get finalSelectionEnd(){if(this.isSelectAllActive)return[this._bufferService.cols,this._bufferService.buffer.ybase+this._bufferService.rows-1];if(this.selectionStart){if(!this.selectionEnd||this.areSelectionValuesReversed()){let e=this.selectionStart[0]+this.selectionStartLength;return e>this._bufferService.cols?e%this._bufferService.cols===0?[this._bufferService.cols,this.selectionStart[1]+Math.floor(e/this._bufferService.cols)-1]:[e%this._bufferService.cols,this.selectionStart[1]+Math.floor(e/this._bufferService.cols)]:[e,this.selectionStart[1]]}if(this.selectionStartLength&&this.selectionEnd[1]===this.selectionStart[1]){let e=this.selectionStart[0]+this.selectionStartLength;return e>this._bufferService.cols?[e%this._bufferService.cols,this.selectionStart[1]+Math.floor(e/this._bufferService.cols)]:[Math.max(e,this.selectionEnd[0]),this.selectionEnd[1]]}return this.selectionEnd}}areSelectionValuesReversed(){let e=this.selectionStart,t=this.selectionEnd;return!(!e||!t)&&(e[1]>t[1]||e[1]===t[1]&&e[0]>t[0])}handleTrim(e){return this.selectionStart&&(this.selectionStart[1]-=e),this.selectionEnd&&(this.selectionEnd[1]-=e),this.selectionEnd&&this.selectionEnd[1]<0?(this.clearSelection(),!0):(this.selectionStart&&this.selectionStart[1]<0&&(this.selectionStart[1]=0),!1)}};function Ja(e,t){if(e.start.y>e.end.y)throw new Error(`Buffer range end (${e.end.x}, ${e.end.y}) cannot be before start (${e.start.x}, ${e.start.y})`);return t*(e.end.y-e.start.y)+(e.end.x-e.start.x+1)}var Za=new RegExp(" ","g"),Qa=class extends Dr{constructor(e,t,s,i,r,n,o,a,l){super(),this._element=e,this._screenElement=t,this._linkifier=s,this._bufferService=i,this._coreService=r,this._mouseService=n,this._optionsService=o,this._renderService=a,this._coreBrowserService=l,this._dragScrollAmount=0,this._enabled=!0,this._workCell=new qi,this._mouseDownTimeStamp=0,this._oldHasSelection=!1,this._oldSelectionStart=void 0,this._oldSelectionEnd=void 0,this._onLinuxMouseSelection=this._register(new Xr),this.onLinuxMouseSelection=this._onLinuxMouseSelection.event,this._onRedrawRequest=this._register(new Xr),this.onRequestRedraw=this._onRedrawRequest.event,this._onSelectionChange=this._register(new Xr),this.onSelectionChange=this._onSelectionChange.event,this._onRequestScrollLines=this._register(new Xr),this.onRequestScrollLines=this._onRequestScrollLines.event,this._mouseMoveListener=e=>this._handleMouseMove(e),this._mouseUpListener=e=>this._handleMouseUp(e),this._coreService.onUserInput(()=>{this.hasSelection&&this.clearSelection()}),this._trimListener=this._bufferService.buffer.lines.onTrim(e=>this._handleTrim(e)),this._register(this._bufferService.buffers.onBufferActivate(e=>this._handleBufferActivate(e))),this.enable(),this._model=new Xa(this._bufferService),this._activeSelectionMode=0,this._register(Pr(()=>{this._removeMouseDownListeners()})),this._register(this._bufferService.onResize(e=>{e.rowsChanged&&this.clearSelection()}))}reset(){this.clearSelection()}disable(){this.clearSelection(),this._enabled=!1}enable(){this._enabled=!0}get selectionStart(){return this._model.finalSelectionStart}get selectionEnd(){return this._model.finalSelectionEnd}get hasSelection(){let e=this._model.finalSelectionStart,t=this._model.finalSelectionEnd;return!(!e||!t)&&(e[0]!==t[0]||e[1]!==t[1])}get selectionText(){let e=this._model.finalSelectionStart,t=this._model.finalSelectionEnd;if(!e||!t)return"";let s=this._bufferService.buffer,i=[];if(3===this._activeSelectionMode){if(e[0]===t[0])return"";let r=e[0]<t[0]?e[0]:t[0],n=e[0]<t[0]?t[0]:e[0];for(let o=e[1];o<=t[1];o++){let e=s.translateBufferLineToString(o,!0,r,n);i.push(e)}}else{let r=e[1]===t[1]?t[0]:void 0;i.push(s.translateBufferLineToString(e[1],!0,e[0],r));for(let r=e[1]+1;r<=t[1]-1;r++){let e=s.lines.get(r),t=s.translateBufferLineToString(r,!0);e?.isWrapped?i[i.length-1]+=t:i.push(t)}if(e[1]!==t[1]){let e=s.lines.get(t[1]),r=s.translateBufferLineToString(t[1],!0,0,t[0]);e&&e.isWrapped?i[i.length-1]+=r:i.push(r)}}return i.map(e=>e.replace(Za," ")).join(Ba?"\r\n":"\n")}clearSelection(){this._model.clearSelection(),this._removeMouseDownListeners(),this.refresh(),this._onSelectionChange.fire()}refresh(e){this._refreshAnimationFrame||(this._refreshAnimationFrame=this._coreBrowserService.window.requestAnimationFrame(()=>this._refresh())),Oa&&e&&this.selectionText.length&&this._onLinuxMouseSelection.fire(this.selectionText)}_refresh(){this._refreshAnimationFrame=void 0,this._onRedrawRequest.fire({start:this._model.finalSelectionStart,end:this._model.finalSelectionEnd,columnSelectMode:3===this._activeSelectionMode})}_isClickInSelection(e){let t=this._getMouseBufferCoords(e),s=this._model.finalSelectionStart,i=this._model.finalSelectionEnd;return!!(s&&i&&t)&&this._areCoordsInSelection(t,s,i)}isCellInSelection(e,t){let s=this._model.finalSelectionStart,i=this._model.finalSelectionEnd;return!(!s||!i)&&this._areCoordsInSelection([e,t],s,i)}_areCoordsInSelection(e,t,s){return e[1]>t[1]&&e[1]<s[1]||t[1]===s[1]&&e[1]===t[1]&&e[0]>=t[0]&&e[0]<s[0]||t[1]<s[1]&&e[1]===s[1]&&e[0]<s[0]||t[1]<s[1]&&e[1]===t[1]&&e[0]>=t[0]}_selectWordAtCursor(e,t){let s=this._linkifier.currentLink?.link?.range;if(s)return this._model.selectionStart=[s.start.x-1,s.start.y-1],this._model.selectionStartLength=Ja(s,this._bufferService.cols),this._model.selectionEnd=void 0,!0;let i=this._getMouseBufferCoords(e);return!!i&&(this._selectWordAt(i,t),this._model.selectionEnd=void 0,!0)}selectAll(){this._model.isSelectAllActive=!0,this.refresh(),this._onSelectionChange.fire()}selectLines(e,t){this._model.clearSelection(),e=Math.max(e,0),t=Math.min(t,this._bufferService.buffer.lines.length-1),this._model.selectionStart=[0,e],this._model.selectionEnd=[this._bufferService.cols,t],this.refresh(),this._onSelectionChange.fire()}_handleTrim(e){this._model.handleTrim(e)&&this.refresh()}_getMouseBufferCoords(e){let t=this._mouseService.getCoords(e,this._screenElement,this._bufferService.cols,this._bufferService.rows,!0);if(t)return t[0]--,t[1]--,t[1]+=this._bufferService.buffer.ydisp,t}_getMouseEventScrollAmount(e){let t=wa(this._coreBrowserService.window,e,this._screenElement)[1],s=this._renderService.dimensions.css.canvas.height;return t>=0&&t<=s?0:(t>s&&(t-=s),t=Math.min(Math.max(t,-50),50),t/=50,t/Math.abs(t)+Math.round(14*t))}shouldForceSelection(e){return Da?e.altKey&&this._optionsService.rawOptions.macOptionClickForcesSelection:e.shiftKey}handleMouseDown(e){if(this._mouseDownTimeStamp=e.timeStamp,(2!==e.button||!this.hasSelection)&&0===e.button){if(!this._enabled){if(!this.shouldForceSelection(e))return;e.stopPropagation()}e.preventDefault(),this._dragScrollAmount=0,this._enabled&&e.shiftKey?this._handleIncrementalClick(e):1===e.detail?this._handleSingleClick(e):2===e.detail?this._handleDoubleClick(e):3===e.detail&&this._handleTripleClick(e),this._addMouseDownListeners(),this.refresh(!0)}}_addMouseDownListeners(){this._screenElement.ownerDocument&&(this._screenElement.ownerDocument.addEventListener("mousemove",this._mouseMoveListener),this._screenElement.ownerDocument.addEventListener("mouseup",this._mouseUpListener)),this._dragScrollIntervalTimer=this._coreBrowserService.window.setInterval(()=>this._dragScroll(),50)}_removeMouseDownListeners(){this._screenElement.ownerDocument&&(this._screenElement.ownerDocument.removeEventListener("mousemove",this._mouseMoveListener),this._screenElement.ownerDocument.removeEventListener("mouseup",this._mouseUpListener)),this._coreBrowserService.window.clearInterval(this._dragScrollIntervalTimer),this._dragScrollIntervalTimer=void 0}_handleIncrementalClick(e){this._model.selectionStart&&(this._model.selectionEnd=this._getMouseBufferCoords(e))}_handleSingleClick(e){if(this._model.selectionStartLength=0,this._model.isSelectAllActive=!1,this._activeSelectionMode=this.shouldColumnSelect(e)?3:0,this._model.selectionStart=this._getMouseBufferCoords(e),!this._model.selectionStart)return;this._model.selectionEnd=void 0;let t=this._bufferService.buffer.lines.get(this._model.selectionStart[1]);t&&t.length!==this._model.selectionStart[0]&&0===t.hasWidth(this._model.selectionStart[0])&&this._model.selectionStart[0]++}_handleDoubleClick(e){this._selectWordAtCursor(e,!0)&&(this._activeSelectionMode=1)}_handleTripleClick(e){let t=this._getMouseBufferCoords(e);t&&(this._activeSelectionMode=2,this._selectLineAt(t[1]))}shouldColumnSelect(e){return e.altKey&&!(Da&&this._optionsService.rawOptions.macOptionClickForcesSelection)}_handleMouseMove(e){if(e.stopImmediatePropagation(),!this._model.selectionStart)return;let t=this._model.selectionEnd?[this._model.selectionEnd[0],this._model.selectionEnd[1]]:null;if(this._model.selectionEnd=this._getMouseBufferCoords(e),!this._model.selectionEnd)return void this.refresh(!0);2===this._activeSelectionMode?this._model.selectionEnd[1]<this._model.selectionStart[1]?this._model.selectionEnd[0]=0:this._model.selectionEnd[0]=this._bufferService.cols:1===this._activeSelectionMode&&this._selectToWordAt(this._model.selectionEnd),this._dragScrollAmount=this._getMouseEventScrollAmount(e),3!==this._activeSelectionMode&&(this._dragScrollAmount>0?this._model.selectionEnd[0]=this._bufferService.cols:this._dragScrollAmount<0&&(this._model.selectionEnd[0]=0));let s=this._bufferService.buffer;if(this._model.selectionEnd[1]<s.lines.length){let e=s.lines.get(this._model.selectionEnd[1]);e&&0===e.hasWidth(this._model.selectionEnd[0])&&this._model.selectionEnd[0]<this._bufferService.cols&&this._model.selectionEnd[0]++}(!t||t[0]!==this._model.selectionEnd[0]||t[1]!==this._model.selectionEnd[1])&&this.refresh(!0)}_dragScroll(){if(this._model.selectionEnd&&this._model.selectionStart&&this._dragScrollAmount){this._onRequestScrollLines.fire({amount:this._dragScrollAmount,suppressScrollEvent:!1});let e=this._bufferService.buffer;this._dragScrollAmount>0?(3!==this._activeSelectionMode&&(this._model.selectionEnd[0]=this._bufferService.cols),this._model.selectionEnd[1]=Math.min(e.ydisp+this._bufferService.rows,e.lines.length-1)):(3!==this._activeSelectionMode&&(this._model.selectionEnd[0]=0),this._model.selectionEnd[1]=e.ydisp),this.refresh()}}_handleMouseUp(e){let t=e.timeStamp-this._mouseDownTimeStamp;if(this._removeMouseDownListeners(),this.selectionText.length<=1&&t<500&&e.altKey&&this._optionsService.rawOptions.altClickMovesCursor){if(this._bufferService.buffer.ybase===this._bufferService.buffer.ydisp){let t=this._mouseService.getCoords(e,this._element,this._bufferService.cols,this._bufferService.rows,!1);if(t&&void 0!==t[0]&&void 0!==t[1]){let e=Ua(t[0]-1,t[1]-1,this._bufferService,this._coreService.decPrivateModes.applicationCursorKeys);this._coreService.triggerDataEvent(e,!0)}}}else this._fireEventIfSelectionChanged()}_fireEventIfSelectionChanged(){let e=this._model.finalSelectionStart,t=this._model.finalSelectionEnd,s=!(!e||!t||e[0]===t[0]&&e[1]===t[1]);s?!e||!t||(!this._oldSelectionStart||!this._oldSelectionEnd||e[0]!==this._oldSelectionStart[0]||e[1]!==this._oldSelectionStart[1]||t[0]!==this._oldSelectionEnd[0]||t[1]!==this._oldSelectionEnd[1])&&this._fireOnSelectionChange(e,t,s):this._oldHasSelection&&this._fireOnSelectionChange(e,t,s)}_fireOnSelectionChange(e,t,s){this._oldSelectionStart=e,this._oldSelectionEnd=t,this._oldHasSelection=s,this._onSelectionChange.fire()}_handleBufferActivate(e){this.clearSelection(),this._trimListener.dispose(),this._trimListener=e.activeBuffer.lines.onTrim(e=>this._handleTrim(e))}_convertViewportColToCharacterIndex(e,t){let s=t;for(let i=0;t>=i;i++){let r=e.loadCell(i,this._workCell).getChars().length;0===this._workCell.getWidth()?s--:r>1&&t!==i&&(s+=r-1)}return s}setSelection(e,t,s){this._model.clearSelection(),this._removeMouseDownListeners(),this._model.selectionStart=[e,t],this._model.selectionStartLength=s,this.refresh(),this._fireEventIfSelectionChanged()}rightClickSelect(e){this._isClickInSelection(e)||(this._selectWordAtCursor(e,!1)&&this.refresh(!0),this._fireEventIfSelectionChanged())}_getWordAt(e,t,s=!0,i=!0){if(e[0]>=this._bufferService.cols)return;let r=this._bufferService.buffer,n=r.lines.get(e[1]);if(!n)return;let o=r.translateBufferLineToString(e[1],!1),a=this._convertViewportColToCharacterIndex(n,e[0]),l=a,h=e[0]-a,c=0,d=0,u=0,p=0;if(" "===o.charAt(a)){for(;a>0&&" "===o.charAt(a-1);)a--;for(;l<o.length&&" "===o.charAt(l+1);)l++}else{let t=e[0],s=e[0];0===n.getWidth(t)&&(c++,t--),2===n.getWidth(s)&&(d++,s++);let i=n.getString(s).length;for(i>1&&(p+=i-1,l+=i-1);t>0&&a>0&&!this._isCharWordSeparator(n.loadCell(t-1,this._workCell));){n.loadCell(t-1,this._workCell);let e=this._workCell.getChars().length;0===this._workCell.getWidth()?(c++,t--):e>1&&(u+=e-1,a-=e-1),a--,t--}for(;s<n.length&&l+1<o.length&&!this._isCharWordSeparator(n.loadCell(s+1,this._workCell));){n.loadCell(s+1,this._workCell);let e=this._workCell.getChars().length;2===this._workCell.getWidth()?(d++,s++):e>1&&(p+=e-1,l+=e-1),l++,s++}}l++;let _=a+h-c+u,f=Math.min(this._bufferService.cols,l-a+c+d-u-p);if(t||""!==o.slice(a,l).trim()){if(s&&0===_&&32!==n.getCodePoint(0)){let t=r.lines.get(e[1]-1);if(t&&n.isWrapped&&32!==t.getCodePoint(this._bufferService.cols-1)){let t=this._getWordAt([this._bufferService.cols-1,e[1]-1],!1,!0,!1);if(t){let e=this._bufferService.cols-t.start;_-=e,f+=e}}}if(i&&_+f===this._bufferService.cols&&32!==n.getCodePoint(this._bufferService.cols-1)){let t=r.lines.get(e[1]+1);if(t?.isWrapped&&32!==t.getCodePoint(0)){let t=this._getWordAt([0,e[1]+1],!1,!1,!0);t&&(f+=t.length)}}return{start:_,length:f}}}_selectWordAt(e,t){let s=this._getWordAt(e,t);if(s){for(;s.start<0;)s.start+=this._bufferService.cols,e[1]--;this._model.selectionStart=[s.start,e[1]],this._model.selectionStartLength=s.length}}_selectToWordAt(e){let t=this._getWordAt(e,!0);if(t){let s=e[1];for(;t.start<0;)t.start+=this._bufferService.cols,s--;if(!this._model.areSelectionValuesReversed())for(;t.start+t.length>this._bufferService.cols;)t.length-=this._bufferService.cols,s++;this._model.selectionEnd=[this._model.areSelectionValuesReversed()?t.start:t.start+t.length,s]}}_isCharWordSeparator(e){return 0!==e.getWidth()&&this._optionsService.rawOptions.wordSeparator.indexOf(e.getChars())>=0}_selectLineAt(e){let t=this._bufferService.buffer.getWrappedRangeForLine(e),s={start:{x:0,y:t.first},end:{x:this._bufferService.cols-1,y:t.last}};this._model.selectionStart=[0,t.first],this._model.selectionEnd=void 0,this._model.selectionStartLength=Ja(s,this._bufferService.cols)}};Qa=Pi([Ai(3,Zi),Ai(4,er),Ai(5,ur),Ai(6,rr),Ai(7,pr),Ai(8,dr)],Qa);var el=class{constructor(){this._data={}}set(e,t,s){this._data[e]||(this._data[e]={}),this._data[e][t]=s}get(e,t){return this._data[e]?this._data[e][t]:void 0}clear(){this._data={}}},tl=class{constructor(){this._color=new el,this._css=new el}setCss(e,t,s){this._css.set(e,t,s)}getCss(e,t){return this._css.get(e,t)}setColor(e,t,s){this._color.set(e,t,s)}getColor(e,t){return this._color.get(e,t)}clear(){this._color.clear(),this._css.clear()}},sl=Object.freeze((()=>{let e=[Ko.toColor("#2e3436"),Ko.toColor("#cc0000"),Ko.toColor("#4e9a06"),Ko.toColor("#c4a000"),Ko.toColor("#3465a4"),Ko.toColor("#75507b"),Ko.toColor("#06989a"),Ko.toColor("#d3d7cf"),Ko.toColor("#555753"),Ko.toColor("#ef2929"),Ko.toColor("#8ae234"),Ko.toColor("#fce94f"),Ko.toColor("#729fcf"),Ko.toColor("#ad7fa8"),Ko.toColor("#34e2e2"),Ko.toColor("#eeeeec")],t=[0,95,135,175,215,255];for(let s=0;s<216;s++){let i=t[s/36%6|0],r=t[s/6%6|0],n=t[s%6];e.push({css:Wo.toCss(i,r,n),rgba:Wo.toRgba(i,r,n)})}for(let t=0;t<24;t++){let s=8+10*t;e.push({css:Wo.toCss(s,s,s),rgba:Wo.toRgba(s,s,s)})}return e})()),il=Ko.toColor("#ffffff"),rl=Ko.toColor("#000000"),nl=Ko.toColor("#ffffff"),ol=rl,al={css:"rgba(255, 255, 255, 0.3)",rgba:4294967117},ll=il,hl=class extends Dr{constructor(e){super(),this._optionsService=e,this._contrastCache=new tl,this._halfContrastCache=new tl,this._onChangeColors=this._register(new Xr),this.onChangeColors=this._onChangeColors.event,this._colors={foreground:il,background:rl,cursor:nl,cursorAccent:ol,selectionForeground:void 0,selectionBackgroundTransparent:al,selectionBackgroundOpaque:Uo.blend(rl,al),selectionInactiveBackgroundTransparent:al,selectionInactiveBackgroundOpaque:Uo.blend(rl,al),scrollbarSliderBackground:Uo.opacity(il,.2),scrollbarSliderHoverBackground:Uo.opacity(il,.4),scrollbarSliderActiveBackground:Uo.opacity(il,.5),overviewRulerBorder:il,ansi:sl.slice(),contrastCache:this._contrastCache,halfContrastCache:this._halfContrastCache},this._updateRestoreColors(),this._setTheme(this._optionsService.rawOptions.theme),this._register(this._optionsService.onSpecificOptionChange("minimumContrastRatio",()=>this._contrastCache.clear())),this._register(this._optionsService.onSpecificOptionChange("theme",()=>this._setTheme(this._optionsService.rawOptions.theme)))}get colors(){return this._colors}_setTheme(e={}){let t=this._colors;if(t.foreground=cl(e.foreground,il),t.background=cl(e.background,rl),t.cursor=Uo.blend(t.background,cl(e.cursor,nl)),t.cursorAccent=Uo.blend(t.background,cl(e.cursorAccent,ol)),t.selectionBackgroundTransparent=cl(e.selectionBackground,al),t.selectionBackgroundOpaque=Uo.blend(t.background,t.selectionBackgroundTransparent),t.selectionInactiveBackgroundTransparent=cl(e.selectionInactiveBackground,t.selectionBackgroundTransparent),t.selectionInactiveBackgroundOpaque=Uo.blend(t.background,t.selectionInactiveBackgroundTransparent),t.selectionForeground=e.selectionForeground?cl(e.selectionForeground,Jo):void 0,t.selectionForeground===Jo&&(t.selectionForeground=void 0),Uo.isOpaque(t.selectionBackgroundTransparent)&&(t.selectionBackgroundTransparent=Uo.opacity(t.selectionBackgroundTransparent,.3)),Uo.isOpaque(t.selectionInactiveBackgroundTransparent)&&(t.selectionInactiveBackgroundTransparent=Uo.opacity(t.selectionInactiveBackgroundTransparent,.3)),t.scrollbarSliderBackground=cl(e.scrollbarSliderBackground,Uo.opacity(t.foreground,.2)),t.scrollbarSliderHoverBackground=cl(e.scrollbarSliderHoverBackground,Uo.opacity(t.foreground,.4)),t.scrollbarSliderActiveBackground=cl(e.scrollbarSliderActiveBackground,Uo.opacity(t.foreground,.5)),t.overviewRulerBorder=cl(e.overviewRulerBorder,ll),t.ansi=sl.slice(),t.ansi[0]=cl(e.black,sl[0]),t.ansi[1]=cl(e.red,sl[1]),t.ansi[2]=cl(e.green,sl[2]),t.ansi[3]=cl(e.yellow,sl[3]),t.ansi[4]=cl(e.blue,sl[4]),t.ansi[5]=cl(e.magenta,sl[5]),t.ansi[6]=cl(e.cyan,sl[6]),t.ansi[7]=cl(e.white,sl[7]),t.ansi[8]=cl(e.brightBlack,sl[8]),t.ansi[9]=cl(e.brightRed,sl[9]),t.ansi[10]=cl(e.brightGreen,sl[10]),t.ansi[11]=cl(e.brightYellow,sl[11]),t.ansi[12]=cl(e.brightBlue,sl[12]),t.ansi[13]=cl(e.brightMagenta,sl[13]),t.ansi[14]=cl(e.brightCyan,sl[14]),t.ansi[15]=cl(e.brightWhite,sl[15]),e.extendedAnsi){let s=Math.min(t.ansi.length-16,e.extendedAnsi.length);for(let i=0;i<s;i++)t.ansi[i+16]=cl(e.extendedAnsi[i],sl[i+16])}this._contrastCache.clear(),this._halfContrastCache.clear(),this._updateRestoreColors(),this._onChangeColors.fire(this.colors)}restoreColor(e){this._restoreColor(e),this._onChangeColors.fire(this.colors)}_restoreColor(e){if(void 0!==e)switch(e){case 256:this._colors.foreground=this._restoreColors.foreground;break;case 257:this._colors.background=this._restoreColors.background;break;case 258:this._colors.cursor=this._restoreColors.cursor;break;default:this._colors.ansi[e]=this._restoreColors.ansi[e]}else for(let e=0;e<this._restoreColors.ansi.length;++e)this._colors.ansi[e]=this._restoreColors.ansi[e]}modifyColors(e){e(this._colors),this._onChangeColors.fire(this.colors)}_updateRestoreColors(){this._restoreColors={foreground:this._colors.foreground,background:this._colors.background,cursor:this._colors.cursor,ansi:this._colors.ansi.slice()}}};function cl(e,t){if(void 0!==e)try{return Ko.toColor(e)}catch{}return t}hl=Pi([Ai(0,rr)],hl);var dl=class{constructor(...e){this._entries=new Map;for(let[t,s]of e)this.set(t,s)}set(e,t){let s=this._entries.get(e);return this._entries.set(e,t),s}forEach(e){for(let[t,s]of this._entries.entries())e(t,s)}has(e){return this._entries.has(e)}get(e){return this._entries.get(e)}},ul=class{constructor(){this._services=new dl,this._services.set(sr,this)}setService(e,t){this._services.set(e,t)}getService(e){return this._services.get(e)}createInstance(e,...t){let s=function(e){return e[Gi]||[]}(e).sort((e,t)=>e.index-t.index),i=[];for(let t of s){let s=this._services.get(t.id);if(!s)throw new Error(`[createInstance] ${e.name} depends on UNKNOWN service ${t.id._id}.`);i.push(s)}let r=s.length>0?s[0].index:t.length;if(t.length!==r)throw new Error(`[createInstance] First service dependency of ${e.name} at position ${r+1} conflicts with ${t.length} static arguments`);return new e(...t,...i)}},pl={trace:0,debug:1,info:2,warn:3,error:4,off:5},_l=class extends Dr{constructor(e){super(),this._optionsService=e,this._logLevel=5,this._updateLogLevel(),this._register(this._optionsService.onSpecificOptionChange("logLevel",()=>this._updateLogLevel()))}get logLevel(){return this._logLevel}_updateLogLevel(){this._logLevel=pl[this._optionsService.rawOptions.logLevel]}_evalLazyOptionalParams(e){for(let t=0;t<e.length;t++)"function"==typeof e[t]&&(e[t]=e[t]())}_log(e,t,s){this._evalLazyOptionalParams(s),e.call(console,(this._optionsService.options.logger?"":"xterm.js: ")+t,...s)}trace(e,...t){this._logLevel<=0&&this._log(this._optionsService.options.logger?.trace.bind(this._optionsService.options.logger)??console.log,e,t)}debug(e,...t){this._logLevel<=1&&this._log(this._optionsService.options.logger?.debug.bind(this._optionsService.options.logger)??console.log,e,t)}info(e,...t){this._logLevel<=2&&this._log(this._optionsService.options.logger?.info.bind(this._optionsService.options.logger)??console.info,e,t)}warn(e,...t){this._logLevel<=3&&this._log(this._optionsService.options.logger?.warn.bind(this._optionsService.options.logger)??console.warn,e,t)}error(e,...t){this._logLevel<=4&&this._log(this._optionsService.options.logger?.error.bind(this._optionsService.options.logger)??console.error,e,t)}};_l=Pi([Ai(0,rr)],_l);var fl=class extends Dr{constructor(e){super(),this._maxLength=e,this.onDeleteEmitter=this._register(new Xr),this.onDelete=this.onDeleteEmitter.event,this.onInsertEmitter=this._register(new Xr),this.onInsert=this.onInsertEmitter.event,this.onTrimEmitter=this._register(new Xr),this.onTrim=this.onTrimEmitter.event,this._array=new Array(this._maxLength),this._startIndex=0,this._length=0}get maxLength(){return this._maxLength}set maxLength(e){if(this._maxLength===e)return;let t=new Array(e);for(let s=0;s<Math.min(e,this.length);s++)t[s]=this._array[this._getCyclicIndex(s)];this._array=t,this._maxLength=e,this._startIndex=0}get length(){return this._length}set length(e){if(e>this._length)for(let t=this._length;t<e;t++)this._array[t]=void 0;this._length=e}get(e){return this._array[this._getCyclicIndex(e)]}set(e,t){this._array[this._getCyclicIndex(e)]=t}push(e){this._array[this._getCyclicIndex(this._length)]=e,this._length===this._maxLength?(this._startIndex=++this._startIndex%this._maxLength,this.onTrimEmitter.fire(1)):this._length++}recycle(){if(this._length!==this._maxLength)throw new Error("Can only recycle when the buffer is full");return this._startIndex=++this._startIndex%this._maxLength,this.onTrimEmitter.fire(1),this._array[this._getCyclicIndex(this._length-1)]}get isFull(){return this._length===this._maxLength}pop(){return this._array[this._getCyclicIndex(this._length---1)]}splice(e,t,...s){if(t){for(let s=e;s<this._length-t;s++)this._array[this._getCyclicIndex(s)]=this._array[this._getCyclicIndex(s+t)];this._length-=t,this.onDeleteEmitter.fire({index:e,amount:t})}for(let t=this._length-1;t>=e;t--)this._array[this._getCyclicIndex(t+s.length)]=this._array[this._getCyclicIndex(t)];for(let t=0;t<s.length;t++)this._array[this._getCyclicIndex(e+t)]=s[t];if(s.length&&this.onInsertEmitter.fire({index:e,amount:s.length}),this._length+s.length>this._maxLength){let e=this._length+s.length-this._maxLength;this._startIndex+=e,this._length=this._maxLength,this.onTrimEmitter.fire(e)}else this._length+=s.length}trimStart(e){e>this._length&&(e=this._length),this._startIndex+=e,this._length-=e,this.onTrimEmitter.fire(e)}shiftElements(e,t,s){if(!(t<=0)){if(e<0||e>=this._length)throw new Error("start argument out of range");if(e+s<0)throw new Error("Cannot shift elements in list beyond index 0");if(s>0){for(let i=t-1;i>=0;i--)this.set(e+i+s,this.get(e+i));let i=e+t+s-this._length;if(i>0)for(this._length+=i;this._length>this._maxLength;)this._length--,this._startIndex++,this.onTrimEmitter.fire(1)}else for(let i=0;i<t;i++)this.set(e+i+s,this.get(e+i))}}_getCyclicIndex(e){return(this._startIndex+e)%this._maxLength}},gl=Object.freeze(new Vi),vl=0,ml=class e{constructor(e,t,s=!1){this.isWrapped=s,this._combined={},this._extendedAttrs={},this._data=new Uint32Array(3*e);let i=t||qi.fromCharData([0,"",1,0]);for(let t=0;t<e;++t)this.setCell(t,i);this.length=e}get(e){let t=this._data[3*e+0],s=2097151&t;return[this._data[3*e+1],2097152&t?this._combined[e]:s?Fi(s):"",t>>22,2097152&t?this._combined[e].charCodeAt(this._combined[e].length-1):s]}set(e,t){this._data[3*e+1]=t[0],t[1].length>1?(this._combined[e]=t[1],this._data[3*e+0]=2097152|e|t[2]<<22):this._data[3*e+0]=t[1].charCodeAt(0)|t[2]<<22}getWidth(e){return this._data[3*e+0]>>22}hasWidth(e){return 12582912&this._data[3*e+0]}getFg(e){return this._data[3*e+1]}getBg(e){return this._data[3*e+2]}hasContent(e){return 4194303&this._data[3*e+0]}getCodePoint(e){let t=this._data[3*e+0];return 2097152&t?this._combined[e].charCodeAt(this._combined[e].length-1):2097151&t}isCombined(e){return 2097152&this._data[3*e+0]}getString(e){let t=this._data[3*e+0];return 2097152&t?this._combined[e]:2097151&t?Fi(2097151&t):""}isProtected(e){return 536870912&this._data[3*e+2]}loadCell(e,t){return vl=3*e,t.content=this._data[vl+0],t.fg=this._data[vl+1],t.bg=this._data[vl+2],2097152&t.content&&(t.combinedData=this._combined[e]),268435456&t.bg&&(t.extended=this._extendedAttrs[e]),t}setCell(e,t){2097152&t.content&&(this._combined[e]=t.combinedData),268435456&t.bg&&(this._extendedAttrs[e]=t.extended),this._data[3*e+0]=t.content,this._data[3*e+1]=t.fg,this._data[3*e+2]=t.bg}setCellFromCodepoint(e,t,s,i){268435456&i.bg&&(this._extendedAttrs[e]=i.extended),this._data[3*e+0]=t|s<<22,this._data[3*e+1]=i.fg,this._data[3*e+2]=i.bg}addCodepointToCell(e,t,s){let i=this._data[3*e+0];2097152&i?this._combined[e]+=Fi(t):2097151&i?(this._combined[e]=Fi(2097151&i)+Fi(t),i&=-2097152,i|=2097152):i=t|1<<22,s&&(i&=-12582913,i|=s<<22),this._data[3*e+0]=i}insertCells(e,t,s){if((e%=this.length)&&2===this.getWidth(e-1)&&this.setCellFromCodepoint(e-1,0,1,s),t<this.length-e){let i=new qi;for(let s=this.length-e-t-1;s>=0;--s)this.setCell(e+t+s,this.loadCell(e+s,i));for(let i=0;i<t;++i)this.setCell(e+i,s)}else for(let t=e;t<this.length;++t)this.setCell(t,s);2===this.getWidth(this.length-1)&&this.setCellFromCodepoint(this.length-1,0,1,s)}deleteCells(e,t,s){if(e%=this.length,t<this.length-e){let i=new qi;for(let s=0;s<this.length-e-t;++s)this.setCell(e+s,this.loadCell(e+t+s,i));for(let e=this.length-t;e<this.length;++e)this.setCell(e,s)}else for(let t=e;t<this.length;++t)this.setCell(t,s);e&&2===this.getWidth(e-1)&&this.setCellFromCodepoint(e-1,0,1,s),0===this.getWidth(e)&&!this.hasContent(e)&&this.setCellFromCodepoint(e,0,1,s)}replaceCells(e,t,s,i=!1){if(i)for(e&&2===this.getWidth(e-1)&&!this.isProtected(e-1)&&this.setCellFromCodepoint(e-1,0,1,s),t<this.length&&2===this.getWidth(t-1)&&!this.isProtected(t)&&this.setCellFromCodepoint(t,0,1,s);e<t&&e<this.length;)this.isProtected(e)||this.setCell(e,s),e++;else for(e&&2===this.getWidth(e-1)&&this.setCellFromCodepoint(e-1,0,1,s),t<this.length&&2===this.getWidth(t-1)&&this.setCellFromCodepoint(t,0,1,s);e<t&&e<this.length;)this.setCell(e++,s)}resize(e,t){if(e===this.length)return 4*this._data.length*2<this._data.buffer.byteLength;let s=3*e;if(e>this.length){if(this._data.buffer.byteLength>=4*s)this._data=new Uint32Array(this._data.buffer,0,s);else{let e=new Uint32Array(s);e.set(this._data),this._data=e}for(let s=this.length;s<e;++s)this.setCell(s,t)}else{this._data=this._data.subarray(0,s);let t=Object.keys(this._combined);for(let s=0;s<t.length;s++){let i=parseInt(t[s],10);i>=e&&delete this._combined[i]}let i=Object.keys(this._extendedAttrs);for(let t=0;t<i.length;t++){let s=parseInt(i[t],10);s>=e&&delete this._extendedAttrs[s]}}return this.length=e,4*s*2<this._data.buffer.byteLength}cleanupMemory(){if(4*this._data.length*2<this._data.buffer.byteLength){let e=new Uint32Array(this._data.length);return e.set(this._data),this._data=e,1}return 0}fill(e,t=!1){if(t)for(let t=0;t<this.length;++t)this.isProtected(t)||this.setCell(t,e);else{this._combined={},this._extendedAttrs={};for(let t=0;t<this.length;++t)this.setCell(t,e)}}copyFrom(e){this.length!==e.length?this._data=new Uint32Array(e._data):this._data.set(e._data),this.length=e.length,this._combined={};for(let t in e._combined)this._combined[t]=e._combined[t];this._extendedAttrs={};for(let t in e._extendedAttrs)this._extendedAttrs[t]=e._extendedAttrs[t];this.isWrapped=e.isWrapped}clone(){let t=new e(0);t._data=new Uint32Array(this._data),t.length=this.length;for(let e in this._combined)t._combined[e]=this._combined[e];for(let e in this._extendedAttrs)t._extendedAttrs[e]=this._extendedAttrs[e];return t.isWrapped=this.isWrapped,t}getTrimmedLength(){for(let e=this.length-1;e>=0;--e)if(4194303&this._data[3*e+0])return e+(this._data[3*e+0]>>22);return 0}getNoBgTrimmedLength(){for(let e=this.length-1;e>=0;--e)if(4194303&this._data[3*e+0]||50331648&this._data[3*e+2])return e+(this._data[3*e+0]>>22);return 0}copyCellsFrom(e,t,s,i,r){let n=e._data;if(r)for(let r=i-1;r>=0;r--){for(let e=0;e<3;e++)this._data[3*(s+r)+e]=n[3*(t+r)+e];268435456&n[3*(t+r)+2]&&(this._extendedAttrs[s+r]=e._extendedAttrs[t+r])}else for(let r=0;r<i;r++){for(let e=0;e<3;e++)this._data[3*(s+r)+e]=n[3*(t+r)+e];268435456&n[3*(t+r)+2]&&(this._extendedAttrs[s+r]=e._extendedAttrs[t+r])}let o=Object.keys(e._combined);for(let i=0;i<o.length;i++){let r=parseInt(o[i],10);r>=t&&(this._combined[r-t+s]=e._combined[r])}}translateToString(e,t,s,i){t=t??0,s=s??this.length,e&&(s=Math.min(s,this.getTrimmedLength())),i&&(i.length=0);let r="";for(;t<s;){let e=this._data[3*t+0],s=2097151&e,n=2097152&e?this._combined[t]:s?Fi(s):Ki;if(r+=n,i)for(let e=0;e<n.length;++e)i.push(t);t+=e>>22||1}return i&&i.push(t),r}};function yl(e,t,s){let i=[],r=e.map((s,i)=>bl(e,i,t)).reduce((e,t)=>e+t),n=0,o=0,a=0;for(;a<r;){if(r-a<s){i.push(r-a);break}n+=s;let l=bl(e,o,t);n>l&&(n-=l,o++);let h=2===e[o].getWidth(n-1);h&&n--;let c=h?s-1:s;i.push(c),a+=c}return i}function bl(e,t,s){if(t===e.length-1)return e[t].getTrimmedLength();let i=!e[t].hasContent(s-1)&&1===e[t].getWidth(s-1),r=2===e[t+1].getWidth(0);return i&&r?s-1:s}var wl=class e{constructor(t){this.line=t,this.isDisposed=!1,this._disposables=[],this._id=e._nextId++,this._onDispose=this.register(new Xr),this.onDispose=this._onDispose.event}get id(){return this._id}dispose(){this.isDisposed||(this.isDisposed=!0,this.line=-1,this._onDispose.fire(),Rr(this._disposables),this._disposables.length=0)}register(e){return this._disposables.push(e),e}};wl._nextId=1;var Sl=wl,xl={},$l=xl.B;xl[0]={"`":"◆",a:"▒",b:"␉",c:"␌",d:"␍",e:"␊",f:"°",g:"±",h:"␤",i:"␋",j:"┘",k:"┐",l:"┌",m:"└",n:"┼",o:"⎺",p:"⎻",q:"─",r:"⎼",s:"⎽",t:"├",u:"┤",v:"┴",w:"┬",x:"│",y:"≤",z:"≥","{":"π","|":"≠","}":"£","~":"·"},xl.A={"#":"£"},xl.B=void 0,xl[4]={"#":"£","@":"¾","[":"ij","\\":"½","]":"|","{":"¨","|":"f","}":"¼","~":"´"},xl.C=xl[5]={"[":"Ä","\\":"Ö","]":"Å","^":"Ü","`":"é","{":"ä","|":"ö","}":"å","~":"ü"},xl.R={"#":"£","@":"à","[":"°","\\":"ç","]":"§","{":"é","|":"ù","}":"è","~":"¨"},xl.Q={"@":"à","[":"â","\\":"ç","]":"ê","^":"î","`":"ô","{":"é","|":"ù","}":"è","~":"û"},xl.K={"@":"§","[":"Ä","\\":"Ö","]":"Ü","{":"ä","|":"ö","}":"ü","~":"ß"},xl.Y={"#":"£","@":"§","[":"°","\\":"ç","]":"é","`":"ù","{":"à","|":"ò","}":"è","~":"ì"},xl.E=xl[6]={"@":"Ä","[":"Æ","\\":"Ø","]":"Å","^":"Ü","`":"ä","{":"æ","|":"ø","}":"å","~":"ü"},xl.Z={"#":"£","@":"§","[":"¡","\\":"Ñ","]":"¿","{":"°","|":"ñ","}":"ç"},xl.H=xl[7]={"@":"É","[":"Ä","\\":"Ö","]":"Å","^":"Ü","`":"é","{":"ä","|":"ö","}":"å","~":"ü"},xl["="]={"#":"ù","@":"à","[":"é","\\":"ç","]":"ê","^":"î",_:"è","`":"ô","{":"ä","|":"ö","}":"ü","~":"û"};var kl=4294967295,Cl=class{constructor(e,t,s){this._hasScrollback=e,this._optionsService=t,this._bufferService=s,this.ydisp=0,this.ybase=0,this.y=0,this.x=0,this.tabs={},this.savedY=0,this.savedX=0,this.savedCurAttrData=gl.clone(),this.savedCharset=$l,this.markers=[],this._nullCell=qi.fromCharData([0,"",1,0]),this._whitespaceCell=qi.fromCharData([0,Ki,1,32]),this._isClearing=!1,this._memoryCleanupQueue=new Na,this._memoryCleanupPosition=0,this._cols=this._bufferService.cols,this._rows=this._bufferService.rows,this.lines=new fl(this._getCorrectBufferLength(this._rows)),this.scrollTop=0,this.scrollBottom=this._rows-1,this.setupTabStops()}getNullCell(e){return e?(this._nullCell.fg=e.fg,this._nullCell.bg=e.bg,this._nullCell.extended=e.extended):(this._nullCell.fg=0,this._nullCell.bg=0,this._nullCell.extended=new ji),this._nullCell}getWhitespaceCell(e){return e?(this._whitespaceCell.fg=e.fg,this._whitespaceCell.bg=e.bg,this._whitespaceCell.extended=e.extended):(this._whitespaceCell.fg=0,this._whitespaceCell.bg=0,this._whitespaceCell.extended=new ji),this._whitespaceCell}getBlankLine(e,t){return new ml(this._bufferService.cols,this.getNullCell(e),t)}get hasScrollback(){return this._hasScrollback&&this.lines.maxLength>this._rows}get isCursorInViewport(){let e=this.ybase+this.y-this.ydisp;return e>=0&&e<this._rows}_getCorrectBufferLength(e){if(!this._hasScrollback)return e;let t=e+this._optionsService.rawOptions.scrollback;return t>kl?kl:t}fillViewportRows(e){if(0===this.lines.length){void 0===e&&(e=gl);let t=this._rows;for(;t--;)this.lines.push(this.getBlankLine(e))}}clear(){this.ydisp=0,this.ybase=0,this.y=0,this.x=0,this.lines=new fl(this._getCorrectBufferLength(this._rows)),this.scrollTop=0,this.scrollBottom=this._rows-1,this.setupTabStops()}resize(e,t){let s=this.getNullCell(gl),i=0,r=this._getCorrectBufferLength(t);if(r>this.lines.maxLength&&(this.lines.maxLength=r),this.lines.length>0){if(this._cols<e)for(let t=0;t<this.lines.length;t++)i+=+this.lines.get(t).resize(e,s);let n=0;if(this._rows<t)for(let i=this._rows;i<t;i++)this.lines.length<t+this.ybase&&(this._optionsService.rawOptions.windowsMode||void 0!==this._optionsService.rawOptions.windowsPty.backend||void 0!==this._optionsService.rawOptions.windowsPty.buildNumber?this.lines.push(new ml(e,s)):this.ybase>0&&this.lines.length<=this.ybase+this.y+n+1?(this.ybase--,n++,this.ydisp>0&&this.ydisp--):this.lines.push(new ml(e,s)));else for(let e=this._rows;e>t;e--)this.lines.length>t+this.ybase&&(this.lines.length>this.ybase+this.y+1?this.lines.pop():(this.ybase++,this.ydisp++));if(r<this.lines.maxLength){let e=this.lines.length-r;e>0&&(this.lines.trimStart(e),this.ybase=Math.max(this.ybase-e,0),this.ydisp=Math.max(this.ydisp-e,0),this.savedY=Math.max(this.savedY-e,0)),this.lines.maxLength=r}this.x=Math.min(this.x,e-1),this.y=Math.min(this.y,t-1),n&&(this.y+=n),this.savedX=Math.min(this.savedX,e-1),this.scrollTop=0}if(this.scrollBottom=t-1,this._isReflowEnabled&&(this._reflow(e,t),this._cols>e))for(let t=0;t<this.lines.length;t++)i+=+this.lines.get(t).resize(e,s);this._cols=e,this._rows=t,this._memoryCleanupQueue.clear(),i>.1*this.lines.length&&(this._memoryCleanupPosition=0,this._memoryCleanupQueue.enqueue(()=>this._batchedMemoryCleanup()))}_batchedMemoryCleanup(){let e=!0;this._memoryCleanupPosition>=this.lines.length&&(this._memoryCleanupPosition=0,e=!1);let t=0;for(;this._memoryCleanupPosition<this.lines.length;)if(t+=this.lines.get(this._memoryCleanupPosition++).cleanupMemory(),t>100)return!0;return e}get _isReflowEnabled(){let e=this._optionsService.rawOptions.windowsPty;return e&&e.buildNumber?this._hasScrollback&&"conpty"===e.backend&&e.buildNumber>=21376:this._hasScrollback&&!this._optionsService.rawOptions.windowsMode}_reflow(e,t){this._cols!==e&&(e>this._cols?this._reflowLarger(e,t):this._reflowSmaller(e,t))}_reflowLarger(e,t){let s=this._optionsService.rawOptions.reflowCursorLine,i=function(e,t,s,i,r,n){let o=[];for(let a=0;a<e.length-1;a++){let l=a,h=e.get(++l);if(!h.isWrapped)continue;let c=[e.get(a)];for(;l<e.length&&h.isWrapped;)c.push(h),h=e.get(++l);if(!n&&i>=a&&i<l){a+=c.length-1;continue}let d=0,u=bl(c,d,t),p=1,_=0;for(;p<c.length;){let e=bl(c,p,t),i=e-_,n=s-u,o=Math.min(i,n);c[d].copyCellsFrom(c[p],_,u,o,!1),u+=o,u===s&&(d++,u=0),_+=o,_===e&&(p++,_=0),0===u&&0!==d&&2===c[d-1].getWidth(s-1)&&(c[d].copyCellsFrom(c[d-1],s-1,u++,1,!1),c[d-1].setCell(s-1,r))}c[d].replaceCells(u,s,r);let f=0;for(let e=c.length-1;e>0&&(e>d||0===c[e].getTrimmedLength());e--)f++;f>0&&(o.push(a+c.length-f),o.push(f)),a+=c.length-1}return o}(this.lines,this._cols,e,this.ybase+this.y,this.getNullCell(gl),s);if(i.length>0){let s=function(e,t){let s=[],i=0,r=t[i],n=0;for(let o=0;o<e.length;o++)if(r===o){let s=t[++i];e.onDeleteEmitter.fire({index:o-n,amount:s}),o+=s-1,n+=s,r=t[++i]}else s.push(o);return{layout:s,countRemoved:n}}(this.lines,i);(function(e,t){let s=[];for(let i=0;i<t.length;i++)s.push(e.get(t[i]));for(let t=0;t<s.length;t++)e.set(t,s[t]);e.length=t.length})(this.lines,s.layout),this._reflowLargerAdjustViewport(e,t,s.countRemoved)}}_reflowLargerAdjustViewport(e,t,s){let i=this.getNullCell(gl),r=s;for(;r-- >0;)0===this.ybase?(this.y>0&&this.y--,this.lines.length<t&&this.lines.push(new ml(e,i))):(this.ydisp===this.ybase&&this.ydisp--,this.ybase--);this.savedY=Math.max(this.savedY-s,0)}_reflowSmaller(e,t){let s=this._optionsService.rawOptions.reflowCursorLine,i=this.getNullCell(gl),r=[],n=0;for(let o=this.lines.length-1;o>=0;o--){let a=this.lines.get(o);if(!a||!a.isWrapped&&a.getTrimmedLength()<=e)continue;let l=[a];for(;a.isWrapped&&o>0;)a=this.lines.get(--o),l.unshift(a);if(!s){let e=this.ybase+this.y;if(e>=o&&e<o+l.length)continue}let h,c=l[l.length-1].getTrimmedLength(),d=yl(l,this._cols,e),u=d.length-l.length;h=0===this.ybase&&this.y!==this.lines.length-1?Math.max(0,this.y-this.lines.maxLength+u):Math.max(0,this.lines.length-this.lines.maxLength+u);let p=[];for(let e=0;e<u;e++){let e=this.getBlankLine(gl,!0);p.push(e)}p.length>0&&(r.push({start:o+l.length+n,newLines:p}),n+=p.length),l.push(...p);let _=d.length-1,f=d[_];0===f&&(_--,f=d[_]);let g=l.length-u-1,v=c;for(;g>=0;){let e=Math.min(v,f);if(void 0===l[_])break;if(l[_].copyCellsFrom(l[g],v-e,f-e,e,!0),f-=e,0===f&&(_--,f=d[_]),v-=e,0===v){g--,v=bl(l,Math.max(g,0),this._cols)}}for(let t=0;t<l.length;t++)d[t]<e&&l[t].setCell(d[t],i);let m=u-h;for(;m-- >0;)0===this.ybase?this.y<t-1?(this.y++,this.lines.pop()):(this.ybase++,this.ydisp++):this.ybase<Math.min(this.lines.maxLength,this.lines.length+n)-t&&(this.ybase===this.ydisp&&this.ydisp++,this.ybase++);this.savedY=Math.min(this.savedY+u,this.ybase+t-1)}if(r.length>0){let e=[],t=[];for(let e=0;e<this.lines.length;e++)t.push(this.lines.get(e));let s=this.lines.length,i=s-1,o=0,a=r[o];this.lines.length=Math.min(this.lines.maxLength,this.lines.length+n);let l=0;for(let h=Math.min(this.lines.maxLength-1,s+n-1);h>=0;h--)if(a&&a.start>i+l){for(let e=a.newLines.length-1;e>=0;e--)this.lines.set(h--,a.newLines[e]);h++,e.push({index:i+1,amount:a.newLines.length}),l+=a.newLines.length,a=r[++o]}else this.lines.set(h,t[i--]);let h=0;for(let t=e.length-1;t>=0;t--)e[t].index+=h,this.lines.onInsertEmitter.fire(e[t]),h+=e[t].amount;let c=Math.max(0,s+n-this.lines.maxLength);c>0&&this.lines.onTrimEmitter.fire(c)}}translateBufferLineToString(e,t,s=0,i){let r=this.lines.get(e);return r?r.translateToString(t,s,i):""}getWrappedRangeForLine(e){let t=e,s=e;for(;t>0&&this.lines.get(t).isWrapped;)t--;for(;s+1<this.lines.length&&this.lines.get(s+1).isWrapped;)s++;return{first:t,last:s}}setupTabStops(e){for(null!=e?this.tabs[e]||(e=this.prevStop(e)):(this.tabs={},e=0);e<this._cols;e+=this._optionsService.rawOptions.tabStopWidth)this.tabs[e]=!0}prevStop(e){for(null==e&&(e=this.x);!this.tabs[--e]&&e>0;);return e>=this._cols?this._cols-1:e<0?0:e}nextStop(e){for(null==e&&(e=this.x);!this.tabs[++e]&&e<this._cols;);return e>=this._cols?this._cols-1:e<0?0:e}clearMarkers(e){this._isClearing=!0;for(let t=0;t<this.markers.length;t++)this.markers[t].line===e&&(this.markers[t].dispose(),this.markers.splice(t--,1));this._isClearing=!1}clearAllMarkers(){this._isClearing=!0;for(let e=0;e<this.markers.length;e++)this.markers[e].dispose();this.markers.length=0,this._isClearing=!1}addMarker(e){let t=new Sl(e);return this.markers.push(t),t.register(this.lines.onTrim(e=>{t.line-=e,t.line<0&&t.dispose()})),t.register(this.lines.onInsert(e=>{t.line>=e.index&&(t.line+=e.amount)})),t.register(this.lines.onDelete(e=>{t.line>=e.index&&t.line<e.index+e.amount&&t.dispose(),t.line>e.index&&(t.line-=e.amount)})),t.register(t.onDispose(()=>this._removeMarker(t))),t}_removeMarker(e){this._isClearing||this.markers.splice(this.markers.indexOf(e),1)}},El=class extends Dr{constructor(e,t){super(),this._optionsService=e,this._bufferService=t,this._onBufferActivate=this._register(new Xr),this.onBufferActivate=this._onBufferActivate.event,this.reset(),this._register(this._optionsService.onSpecificOptionChange("scrollback",()=>this.resize(this._bufferService.cols,this._bufferService.rows))),this._register(this._optionsService.onSpecificOptionChange("tabStopWidth",()=>this.setupTabStops()))}reset(){this._normal=new Cl(!0,this._optionsService,this._bufferService),this._normal.fillViewportRows(),this._alt=new Cl(!1,this._optionsService,this._bufferService),this._activeBuffer=this._normal,this._onBufferActivate.fire({activeBuffer:this._normal,inactiveBuffer:this._alt}),this.setupTabStops()}get alt(){return this._alt}get active(){return this._activeBuffer}get normal(){return this._normal}activateNormalBuffer(){this._activeBuffer!==this._normal&&(this._normal.x=this._alt.x,this._normal.y=this._alt.y,this._alt.clearAllMarkers(),this._alt.clear(),this._activeBuffer=this._normal,this._onBufferActivate.fire({activeBuffer:this._normal,inactiveBuffer:this._alt}))}activateAltBuffer(e){this._activeBuffer!==this._alt&&(this._alt.fillViewportRows(e),this._alt.x=this._normal.x,this._alt.y=this._normal.y,this._activeBuffer=this._alt,this._onBufferActivate.fire({activeBuffer:this._alt,inactiveBuffer:this._normal}))}resize(e,t){this._normal.resize(e,t),this._alt.resize(e,t),this.setupTabStops(e)}setupTabStops(e){this._normal.setupTabStops(e),this._alt.setupTabStops(e)}},Rl=class extends Dr{constructor(e){super(),this.isUserScrolling=!1,this._onResize=this._register(new Xr),this.onResize=this._onResize.event,this._onScroll=this._register(new Xr),this.onScroll=this._onScroll.event,this.cols=Math.max(e.rawOptions.cols||0,2),this.rows=Math.max(e.rawOptions.rows||0,1),this.buffers=this._register(new El(e,this)),this._register(this.buffers.onBufferActivate(e=>{this._onScroll.fire(e.activeBuffer.ydisp)}))}get buffer(){return this.buffers.active}resize(e,t){let s=this.cols!==e,i=this.rows!==t;this.cols=e,this.rows=t,this.buffers.resize(e,t),this._onResize.fire({cols:e,rows:t,colsChanged:s,rowsChanged:i})}reset(){this.buffers.reset(),this.isUserScrolling=!1}scroll(e,t=!1){let s,i=this.buffer;s=this._cachedBlankLine,(!s||s.length!==this.cols||s.getFg(0)!==e.fg||s.getBg(0)!==e.bg)&&(s=i.getBlankLine(e,t),this._cachedBlankLine=s),s.isWrapped=t;let r=i.ybase+i.scrollTop,n=i.ybase+i.scrollBottom;if(0===i.scrollTop){let e=i.lines.isFull;n===i.lines.length-1?e?i.lines.recycle().copyFrom(s):i.lines.push(s.clone()):i.lines.splice(n+1,0,s.clone()),e?this.isUserScrolling&&(i.ydisp=Math.max(i.ydisp-1,0)):(i.ybase++,this.isUserScrolling||i.ydisp++)}else{let e=n-r+1;i.lines.shiftElements(r+1,e-1,-1),i.lines.set(n,s.clone())}this.isUserScrolling||(i.ydisp=i.ybase),this._onScroll.fire(i.ydisp)}scrollLines(e,t){let s=this.buffer;if(e<0){if(0===s.ydisp)return;this.isUserScrolling=!0}else e+s.ydisp>=s.ybase&&(this.isUserScrolling=!1);let i=s.ydisp;s.ydisp=Math.max(Math.min(s.ydisp+e,s.ybase),0),i!==s.ydisp&&(t||this._onScroll.fire(s.ydisp))}};Rl=Pi([Ai(0,rr)],Rl);var Pl={cols:80,rows:24,cursorBlink:!1,cursorStyle:"block",cursorWidth:1,cursorInactiveStyle:"outline",customGlyphs:!0,drawBoldTextInBrightColors:!0,documentOverride:null,fastScrollModifier:"alt",fastScrollSensitivity:5,fontFamily:"monospace",fontSize:15,fontWeight:"normal",fontWeightBold:"bold",ignoreBracketedPasteMode:!1,lineHeight:1,letterSpacing:0,linkHandler:null,logLevel:"info",logger:null,scrollback:1e3,scrollOnEraseInDisplay:!1,scrollOnUserInput:!0,scrollSensitivity:1,screenReaderMode:!1,smoothScrollDuration:0,macOptionIsMeta:!1,macOptionClickForcesSelection:!1,minimumContrastRatio:1,disableStdin:!1,allowProposedApi:!1,allowTransparency:!1,tabStopWidth:8,theme:{},reflowCursorLine:!1,rescaleOverlappingGlyphs:!1,rightClickSelectsWord:Da,windowOptions:{},windowsMode:!1,windowsPty:{},wordSeparator:" ()[]{}',\"`",altClickMovesCursor:!0,convertEol:!1,termName:"xterm",cancelEvents:!1,overviewRuler:{}},Al=["normal","bold","100","200","300","400","500","600","700","800","900"],Tl=class extends Dr{constructor(e){super(),this._onOptionChange=this._register(new Xr),this.onOptionChange=this._onOptionChange.event;let t={...Pl};for(let s in e)if(s in t)try{let i=e[s];t[s]=this._sanitizeAndValidateOption(s,i)}catch(e){console.error(e)}this.rawOptions=t,this.options={...t},this._setupOptions(),this._register(Pr(()=>{this.rawOptions.linkHandler=null,this.rawOptions.documentOverride=null}))}onSpecificOptionChange(e,t){return this.onOptionChange(s=>{s===e&&t(this.rawOptions[e])})}onMultipleOptionChange(e,t){return this.onOptionChange(s=>{-1!==e.indexOf(s)&&t()})}_setupOptions(){let e=e=>{if(!(e in Pl))throw new Error(`No option with key "${e}"`);return this.rawOptions[e]},t=(e,t)=>{if(!(e in Pl))throw new Error(`No option with key "${e}"`);t=this._sanitizeAndValidateOption(e,t),this.rawOptions[e]!==t&&(this.rawOptions[e]=t,this._onOptionChange.fire(e))};for(let s in this.rawOptions){let i={get:e.bind(this,s),set:t.bind(this,s)};Object.defineProperty(this.options,s,i)}}_sanitizeAndValidateOption(e,t){switch(e){case"cursorStyle":if(t||(t=Pl[e]),!function(e){return"block"===e||"underline"===e||"bar"===e}(t))throw new Error(`"${t}" is not a valid value for ${e}`);break;case"wordSeparator":t||(t=Pl[e]);break;case"fontWeight":case"fontWeightBold":if("number"==typeof t&&1<=t&&t<=1e3)break;t=Al.includes(t)?t:Pl[e];break;case"cursorWidth":t=Math.floor(t);case"lineHeight":case"tabStopWidth":if(t<1)throw new Error(`${e} cannot be less than 1, value: ${t}`);break;case"minimumContrastRatio":t=Math.max(1,Math.min(21,Math.round(10*t)/10));break;case"scrollback":if((t=Math.min(t,4294967295))<0)throw new Error(`${e} cannot be less than 0, value: ${t}`);break;case"fastScrollSensitivity":case"scrollSensitivity":if(t<=0)throw new Error(`${e} cannot be less than or equal to 0, value: ${t}`);break;case"rows":case"cols":if(!t&&0!==t)throw new Error(`${e} must be numeric, value: ${t}`);break;case"windowsPty":t=t??{}}return t}};function Dl(e,t=5){if("object"!=typeof e)return e;let s=Array.isArray(e)?[]:{};for(let i in e)s[i]=t<=1?e[i]:e[i]&&Dl(e[i],t-1);return s}var Ll=Object.freeze({insertMode:!1}),Ml=Object.freeze({applicationCursorKeys:!1,applicationKeypad:!1,bracketedPasteMode:!1,cursorBlink:void 0,cursorStyle:void 0,origin:!1,reverseWraparound:!1,sendFocus:!1,synchronizedOutput:!1,wraparound:!0}),Bl=class extends Dr{constructor(e,t,s){super(),this._bufferService=e,this._logService=t,this._optionsService=s,this.isCursorInitialized=!1,this.isCursorHidden=!1,this._onData=this._register(new Xr),this.onData=this._onData.event,this._onUserInput=this._register(new Xr),this.onUserInput=this._onUserInput.event,this._onBinary=this._register(new Xr),this.onBinary=this._onBinary.event,this._onRequestScrollToBottom=this._register(new Xr),this.onRequestScrollToBottom=this._onRequestScrollToBottom.event,this.modes=Dl(Ll),this.decPrivateModes=Dl(Ml)}reset(){this.modes=Dl(Ll),this.decPrivateModes=Dl(Ml)}triggerDataEvent(e,t=!1){if(this._optionsService.rawOptions.disableStdin)return;let s=this._bufferService.buffer;t&&this._optionsService.rawOptions.scrollOnUserInput&&s.ybase!==s.ydisp&&this._onRequestScrollToBottom.fire(),t&&this._onUserInput.fire(),this._logService.debug(`sending data "${e}"`),this._logService.trace("sending data (codes)",()=>e.split("").map(e=>e.charCodeAt(0))),this._onData.fire(e)}triggerBinaryEvent(e){this._optionsService.rawOptions.disableStdin||(this._logService.debug(`sending binary "${e}"`),this._logService.trace("sending binary (codes)",()=>e.split("").map(e=>e.charCodeAt(0))),this._onBinary.fire(e))}};Bl=Pi([Ai(0,Zi),Ai(1,ir),Ai(2,rr)],Bl);var Ol={NONE:{events:0,restrict:()=>!1},X10:{events:1,restrict:e=>4!==e.button&&1===e.action&&(e.ctrl=!1,e.alt=!1,e.shift=!1,!0)},VT200:{events:19,restrict:e=>32!==e.action},DRAG:{events:23,restrict:e=>!(32===e.action&&3===e.button)},ANY:{events:31,restrict:e=>!0}};function zl(e,t){let s=(e.ctrl?16:0)|(e.shift?4:0)|(e.alt?8:0);return 4===e.button?(s|=64,s|=e.action):(s|=3&e.button,4&e.button&&(s|=64),8&e.button&&(s|=128),32===e.action?s|=32:0===e.action&&!t&&(s|=3)),s}var Il=String.fromCharCode,Nl={DEFAULT:e=>{let t=[zl(e,!1)+32,e.col+32,e.row+32];return t[0]>255||t[1]>255||t[2]>255?"":`[M${Il(t[0])}${Il(t[1])}${Il(t[2])}`},SGR:e=>{let t=0===e.action&&4!==e.button?"m":"M";return`[<${zl(e,!0)};${e.col};${e.row}${t}`},SGR_PIXELS:e=>{let t=0===e.action&&4!==e.button?"m":"M";return`[<${zl(e,!0)};${e.x};${e.y}${t}`}},Fl=class extends Dr{constructor(e,t,s){super(),this._bufferService=e,this._coreService=t,this._optionsService=s,this._protocols={},this._encodings={},this._activeProtocol="",this._activeEncoding="",this._lastEvent=null,this._wheelPartialScroll=0,this._onProtocolChange=this._register(new Xr),this.onProtocolChange=this._onProtocolChange.event;for(let e of Object.keys(Ol))this.addProtocol(e,Ol[e]);for(let e of Object.keys(Nl))this.addEncoding(e,Nl[e]);this.reset()}addProtocol(e,t){this._protocols[e]=t}addEncoding(e,t){this._encodings[e]=t}get activeProtocol(){return this._activeProtocol}get areMouseEventsActive(){return 0!==this._protocols[this._activeProtocol].events}set activeProtocol(e){if(!this._protocols[e])throw new Error(`unknown protocol "${e}"`);this._activeProtocol=e,this._onProtocolChange.fire(this._protocols[e].events)}get activeEncoding(){return this._activeEncoding}set activeEncoding(e){if(!this._encodings[e])throw new Error(`unknown encoding "${e}"`);this._activeEncoding=e}reset(){this.activeProtocol="NONE",this.activeEncoding="DEFAULT",this._lastEvent=null,this._wheelPartialScroll=0}consumeWheelEvent(e,t,s){if(0===e.deltaY||e.shiftKey||void 0===t||void 0===s)return 0;let i=t/s,r=this._applyScrollModifier(e.deltaY,e);return e.deltaMode===WheelEvent.DOM_DELTA_PIXEL?(r/=i+0,Math.abs(e.deltaY)<50&&(r*=.3),this._wheelPartialScroll+=r,r=Math.floor(Math.abs(this._wheelPartialScroll))*(this._wheelPartialScroll>0?1:-1),this._wheelPartialScroll%=1):e.deltaMode===WheelEvent.DOM_DELTA_PAGE&&(r*=this._bufferService.rows),r}_applyScrollModifier(e,t){return t.altKey||t.ctrlKey||t.shiftKey?e*this._optionsService.rawOptions.fastScrollSensitivity*this._optionsService.rawOptions.scrollSensitivity:e*this._optionsService.rawOptions.scrollSensitivity}triggerMouseEvent(e){if(e.col<0||e.col>=this._bufferService.cols||e.row<0||e.row>=this._bufferService.rows||4===e.button&&32===e.action||3===e.button&&32!==e.action||4!==e.button&&(2===e.action||3===e.action)||(e.col++,e.row++,32===e.action&&this._lastEvent&&this._equalEvents(this._lastEvent,e,"SGR_PIXELS"===this._activeEncoding))||!this._protocols[this._activeProtocol].restrict(e))return!1;let t=this._encodings[this._activeEncoding](e);return t&&("DEFAULT"===this._activeEncoding?this._coreService.triggerBinaryEvent(t):this._coreService.triggerDataEvent(t,!0)),this._lastEvent=e,!0}explainEvents(e){return{down:!!(1&e),up:!!(2&e),drag:!!(4&e),move:!!(8&e),wheel:!!(16&e)}}_equalEvents(e,t,s){if(s){if(e.x!==t.x||e.y!==t.y)return!1}else if(e.col!==t.col||e.row!==t.row)return!1;return!(e.button!==t.button||e.action!==t.action||e.ctrl!==t.ctrl||e.alt!==t.alt||e.shift!==t.shift)}};Fl=Pi([Ai(0,Zi),Ai(1,er),Ai(2,rr)],Fl);var Hl,Wl=[[768,879],[1155,1158],[1160,1161],[1425,1469],[1471,1471],[1473,1474],[1476,1477],[1479,1479],[1536,1539],[1552,1557],[1611,1630],[1648,1648],[1750,1764],[1767,1768],[1770,1773],[1807,1807],[1809,1809],[1840,1866],[1958,1968],[2027,2035],[2305,2306],[2364,2364],[2369,2376],[2381,2381],[2385,2388],[2402,2403],[2433,2433],[2492,2492],[2497,2500],[2509,2509],[2530,2531],[2561,2562],[2620,2620],[2625,2626],[2631,2632],[2635,2637],[2672,2673],[2689,2690],[2748,2748],[2753,2757],[2759,2760],[2765,2765],[2786,2787],[2817,2817],[2876,2876],[2879,2879],[2881,2883],[2893,2893],[2902,2902],[2946,2946],[3008,3008],[3021,3021],[3134,3136],[3142,3144],[3146,3149],[3157,3158],[3260,3260],[3263,3263],[3270,3270],[3276,3277],[3298,3299],[3393,3395],[3405,3405],[3530,3530],[3538,3540],[3542,3542],[3633,3633],[3636,3642],[3655,3662],[3761,3761],[3764,3769],[3771,3772],[3784,3789],[3864,3865],[3893,3893],[3895,3895],[3897,3897],[3953,3966],[3968,3972],[3974,3975],[3984,3991],[3993,4028],[4038,4038],[4141,4144],[4146,4146],[4150,4151],[4153,4153],[4184,4185],[4448,4607],[4959,4959],[5906,5908],[5938,5940],[5970,5971],[6002,6003],[6068,6069],[6071,6077],[6086,6086],[6089,6099],[6109,6109],[6155,6157],[6313,6313],[6432,6434],[6439,6440],[6450,6450],[6457,6459],[6679,6680],[6912,6915],[6964,6964],[6966,6970],[6972,6972],[6978,6978],[7019,7027],[7616,7626],[7678,7679],[8203,8207],[8234,8238],[8288,8291],[8298,8303],[8400,8431],[12330,12335],[12441,12442],[43014,43014],[43019,43019],[43045,43046],[64286,64286],[65024,65039],[65056,65059],[65279,65279],[65529,65531]],Ul=[[68097,68099],[68101,68102],[68108,68111],[68152,68154],[68159,68159],[119143,119145],[119155,119170],[119173,119179],[119210,119213],[119362,119364],[917505,917505],[917536,917631],[917760,917999]];var Kl=class{constructor(){if(this.version="6",!Hl){(Hl=new Uint8Array(65536)).fill(1),Hl[0]=0,Hl.fill(0,1,32),Hl.fill(0,127,160),Hl.fill(2,4352,4448),Hl[9001]=2,Hl[9002]=2,Hl.fill(2,11904,42192),Hl[12351]=1,Hl.fill(2,44032,55204),Hl.fill(2,63744,64256),Hl.fill(2,65040,65050),Hl.fill(2,65072,65136),Hl.fill(2,65280,65377),Hl.fill(2,65504,65511);for(let e=0;e<Wl.length;++e)Hl.fill(0,Wl[e][0],Wl[e][1]+1)}}wcwidth(e){return e<32?0:e<127?1:e<65536?Hl[e]:function(e,t){let s,i=0,r=t.length-1;if(e<t[0][0]||e>t[r][1])return!1;for(;r>=i;)if(s=i+r>>1,e>t[s][1])i=s+1;else{if(!(e<t[s][0]))return!0;r=s-1}return!1}(e,Ul)?0:e>=131072&&e<=196605||e>=196608&&e<=262141?2:1}charProperties(e,t){let s=this.wcwidth(e),i=0===s&&0!==t;if(i){let e=Vl.extractWidth(t);0===e?i=!1:e>s&&(s=e)}return Vl.createPropertyValue(0,s,i)}},Vl=class e{constructor(){this._providers=Object.create(null),this._active="",this._onChange=new Xr,this.onChange=this._onChange.event;let e=new Kl;this.register(e),this._active=e.version,this._activeProvider=e}static extractShouldJoin(e){return!!(1&e)}static extractWidth(e){return e>>1&3}static extractCharKind(e){return e>>3}static createPropertyValue(e,t,s=!1){return(16777215&e)<<3|(3&t)<<1|(s?1:0)}dispose(){this._onChange.dispose()}get versions(){return Object.keys(this._providers)}get activeVersion(){return this._active}set activeVersion(e){if(!this._providers[e])throw new Error(`unknown Unicode version "${e}"`);this._active=e,this._activeProvider=this._providers[e],this._onChange.fire(e)}register(e){this._providers[e.version]=e}wcwidth(e){return this._activeProvider.wcwidth(e)}getStringCellWidth(t){let s=0,i=0,r=t.length;for(let n=0;n<r;++n){let o=t.charCodeAt(n);if(55296<=o&&o<=56319){if(++n>=r)return s+this.wcwidth(o);let e=t.charCodeAt(n);56320<=e&&e<=57343?o=1024*(o-55296)+e-56320+65536:s+=this.wcwidth(e)}let a=this.charProperties(o,i),l=e.extractWidth(a);e.extractShouldJoin(a)&&(l-=e.extractWidth(i)),s+=l,i=a}return s}charProperties(e,t){return this._activeProvider.charProperties(e,t)}},jl=class{constructor(){this.glevel=0,this._charsets=[]}reset(){this.charset=void 0,this._charsets=[],this.glevel=0}setgLevel(e){this.glevel=e,this.charset=this._charsets[e]}setgCharset(e,t){this._charsets[e]=t,this.glevel===e&&(this.charset=t)}};function ql(e){let t=e.buffer.lines.get(e.buffer.ybase+e.buffer.y-1)?.get(e.cols-1),s=e.buffer.lines.get(e.buffer.ybase+e.buffer.y);s&&t&&(s.isWrapped=0!==t[3]&&32!==t[3])}var Yl=2147483647,Gl=class e{constructor(e=32,t=32){if(this.maxLength=e,this.maxSubParamsLength=t,t>256)throw new Error("maxSubParamsLength must not be greater than 256");this.params=new Int32Array(e),this.length=0,this._subParams=new Int32Array(t),this._subParamsLength=0,this._subParamsIdx=new Uint16Array(e),this._rejectDigits=!1,this._rejectSubDigits=!1,this._digitIsSub=!1}static fromArray(t){let s=new e;if(!t.length)return s;for(let e=Array.isArray(t[0])?1:0;e<t.length;++e){let i=t[e];if(Array.isArray(i))for(let e=0;e<i.length;++e)s.addSubParam(i[e]);else s.addParam(i)}return s}clone(){let t=new e(this.maxLength,this.maxSubParamsLength);return t.params.set(this.params),t.length=this.length,t._subParams.set(this._subParams),t._subParamsLength=this._subParamsLength,t._subParamsIdx.set(this._subParamsIdx),t._rejectDigits=this._rejectDigits,t._rejectSubDigits=this._rejectSubDigits,t._digitIsSub=this._digitIsSub,t}toArray(){let e=[];for(let t=0;t<this.length;++t){e.push(this.params[t]);let s=this._subParamsIdx[t]>>8,i=255&this._subParamsIdx[t];i-s>0&&e.push(Array.prototype.slice.call(this._subParams,s,i))}return e}reset(){this.length=0,this._subParamsLength=0,this._rejectDigits=!1,this._rejectSubDigits=!1,this._digitIsSub=!1}addParam(e){if(this._digitIsSub=!1,this.length>=this.maxLength)this._rejectDigits=!0;else{if(e<-1)throw new Error("values lesser than -1 are not allowed");this._subParamsIdx[this.length]=this._subParamsLength<<8|this._subParamsLength,this.params[this.length++]=e>Yl?Yl:e}}addSubParam(e){if(this._digitIsSub=!0,this.length){if(this._rejectDigits||this._subParamsLength>=this.maxSubParamsLength)return void(this._rejectSubDigits=!0);if(e<-1)throw new Error("values lesser than -1 are not allowed");this._subParams[this._subParamsLength++]=e>Yl?Yl:e,this._subParamsIdx[this.length-1]++}}hasSubParams(e){return(255&this._subParamsIdx[e])-(this._subParamsIdx[e]>>8)>0}getSubParams(e){let t=this._subParamsIdx[e]>>8,s=255&this._subParamsIdx[e];return s-t>0?this._subParams.subarray(t,s):null}getSubParamsAll(){let e={};for(let t=0;t<this.length;++t){let s=this._subParamsIdx[t]>>8,i=255&this._subParamsIdx[t];i-s>0&&(e[t]=this._subParams.slice(s,i))}return e}addDigit(e){let t;if(this._rejectDigits||!(t=this._digitIsSub?this._subParamsLength:this.length)||this._digitIsSub&&this._rejectSubDigits)return;let s=this._digitIsSub?this._subParams:this.params,i=s[t-1];s[t-1]=~i?Math.min(10*i+e,Yl):e}},Xl=[],Jl=class{constructor(){this._state=0,this._active=Xl,this._id=-1,this._handlers=Object.create(null),this._handlerFb=()=>{},this._stack={paused:!1,loopPosition:0,fallThrough:!1}}registerHandler(e,t){void 0===this._handlers[e]&&(this._handlers[e]=[]);let s=this._handlers[e];return s.push(t),{dispose:()=>{let e=s.indexOf(t);-1!==e&&s.splice(e,1)}}}clearHandler(e){this._handlers[e]&&delete this._handlers[e]}setHandlerFallback(e){this._handlerFb=e}dispose(){this._handlers=Object.create(null),this._handlerFb=()=>{},this._active=Xl}reset(){if(2===this._state)for(let e=this._stack.paused?this._stack.loopPosition-1:this._active.length-1;e>=0;--e)this._active[e].end(!1);this._stack.paused=!1,this._active=Xl,this._id=-1,this._state=0}_start(){if(this._active=this._handlers[this._id]||Xl,this._active.length)for(let e=this._active.length-1;e>=0;e--)this._active[e].start();else this._handlerFb(this._id,"START")}_put(e,t,s){if(this._active.length)for(let i=this._active.length-1;i>=0;i--)this._active[i].put(e,t,s);else this._handlerFb(this._id,"PUT",Hi(e,t,s))}start(){this.reset(),this._state=1}put(e,t,s){if(3!==this._state){if(1===this._state)for(;t<s;){let s=e[t++];if(59===s){this._state=2,this._start();break}if(s<48||57<s)return void(this._state=3);-1===this._id&&(this._id=0),this._id=10*this._id+s-48}2===this._state&&s-t>0&&this._put(e,t,s)}}end(e,t=!0){if(0!==this._state){if(3!==this._state)if(1===this._state&&this._start(),this._active.length){let s=!1,i=this._active.length-1,r=!1;if(this._stack.paused&&(i=this._stack.loopPosition-1,s=t,r=this._stack.fallThrough,this._stack.paused=!1),!r&&!1===s){for(;i>=0&&(s=this._active[i].end(e),!0!==s);i--)if(s instanceof Promise)return this._stack.paused=!0,this._stack.loopPosition=i,this._stack.fallThrough=!1,s;i--}for(;i>=0;i--)if(s=this._active[i].end(!1),s instanceof Promise)return this._stack.paused=!0,this._stack.loopPosition=i,this._stack.fallThrough=!0,s}else this._handlerFb(this._id,"END",e);this._active=Xl,this._id=-1,this._state=0}}},Zl=class{constructor(e){this._handler=e,this._data="",this._hitLimit=!1}start(){this._data="",this._hitLimit=!1}put(e,t,s){this._hitLimit||(this._data+=Hi(e,t,s),this._data.length>1e7&&(this._data="",this._hitLimit=!0))}end(e){let t=!1;if(this._hitLimit)t=!1;else if(e&&(t=this._handler(this._data),t instanceof Promise))return t.then(e=>(this._data="",this._hitLimit=!1,e));return this._data="",this._hitLimit=!1,t}},Ql=[],eh=class{constructor(){this._handlers=Object.create(null),this._active=Ql,this._ident=0,this._handlerFb=()=>{},this._stack={paused:!1,loopPosition:0,fallThrough:!1}}dispose(){this._handlers=Object.create(null),this._handlerFb=()=>{},this._active=Ql}registerHandler(e,t){void 0===this._handlers[e]&&(this._handlers[e]=[]);let s=this._handlers[e];return s.push(t),{dispose:()=>{let e=s.indexOf(t);-1!==e&&s.splice(e,1)}}}clearHandler(e){this._handlers[e]&&delete this._handlers[e]}setHandlerFallback(e){this._handlerFb=e}reset(){if(this._active.length)for(let e=this._stack.paused?this._stack.loopPosition-1:this._active.length-1;e>=0;--e)this._active[e].unhook(!1);this._stack.paused=!1,this._active=Ql,this._ident=0}hook(e,t){if(this.reset(),this._ident=e,this._active=this._handlers[e]||Ql,this._active.length)for(let e=this._active.length-1;e>=0;e--)this._active[e].hook(t);else this._handlerFb(this._ident,"HOOK",t)}put(e,t,s){if(this._active.length)for(let i=this._active.length-1;i>=0;i--)this._active[i].put(e,t,s);else this._handlerFb(this._ident,"PUT",Hi(e,t,s))}unhook(e,t=!0){if(this._active.length){let s=!1,i=this._active.length-1,r=!1;if(this._stack.paused&&(i=this._stack.loopPosition-1,s=t,r=this._stack.fallThrough,this._stack.paused=!1),!r&&!1===s){for(;i>=0&&(s=this._active[i].unhook(e),!0!==s);i--)if(s instanceof Promise)return this._stack.paused=!0,this._stack.loopPosition=i,this._stack.fallThrough=!1,s;i--}for(;i>=0;i--)if(s=this._active[i].unhook(!1),s instanceof Promise)return this._stack.paused=!0,this._stack.loopPosition=i,this._stack.fallThrough=!0,s}else this._handlerFb(this._ident,"UNHOOK",e);this._active=Ql,this._ident=0}},th=new Gl;th.addParam(0);var sh=class{constructor(e){this._handler=e,this._data="",this._params=th,this._hitLimit=!1}hook(e){this._params=e.length>1||e.params[0]?e.clone():th,this._data="",this._hitLimit=!1}put(e,t,s){this._hitLimit||(this._data+=Hi(e,t,s),this._data.length>1e7&&(this._data="",this._hitLimit=!0))}unhook(e){let t=!1;if(this._hitLimit)t=!1;else if(e&&(t=this._handler(this._data,this._params),t instanceof Promise))return t.then(e=>(this._params=th,this._data="",this._hitLimit=!1,e));return this._params=th,this._data="",this._hitLimit=!1,t}},ih=class{constructor(e){this.table=new Uint8Array(e)}setDefault(e,t){this.table.fill(e<<4|t)}add(e,t,s,i){this.table[t<<8|e]=s<<4|i}addMany(e,t,s,i){for(let r=0;r<e.length;r++)this.table[t<<8|e[r]]=s<<4|i}},rh=160,nh=function(){let e=new ih(4095),t=Array.apply(null,Array(256)).map((e,t)=>t),s=(e,s)=>t.slice(e,s),i=s(32,127),r=s(0,24);r.push(25),r.push.apply(r,s(28,32));let n,o=s(0,14);for(n in e.setDefault(1,0),e.addMany(i,0,2,0),o)e.addMany([24,26,153,154],n,3,0),e.addMany(s(128,144),n,3,0),e.addMany(s(144,152),n,3,0),e.add(156,n,0,0),e.add(27,n,11,1),e.add(157,n,4,8),e.addMany([152,158,159],n,0,7),e.add(155,n,11,3),e.add(144,n,11,9);return e.addMany(r,0,3,0),e.addMany(r,1,3,1),e.add(127,1,0,1),e.addMany(r,8,0,8),e.addMany(r,3,3,3),e.add(127,3,0,3),e.addMany(r,4,3,4),e.add(127,4,0,4),e.addMany(r,6,3,6),e.addMany(r,5,3,5),e.add(127,5,0,5),e.addMany(r,2,3,2),e.add(127,2,0,2),e.add(93,1,4,8),e.addMany(i,8,5,8),e.add(127,8,5,8),e.addMany([156,27,24,26,7],8,6,0),e.addMany(s(28,32),8,0,8),e.addMany([88,94,95],1,0,7),e.addMany(i,7,0,7),e.addMany(r,7,0,7),e.add(156,7,0,0),e.add(127,7,0,7),e.add(91,1,11,3),e.addMany(s(64,127),3,7,0),e.addMany(s(48,60),3,8,4),e.addMany([60,61,62,63],3,9,4),e.addMany(s(48,60),4,8,4),e.addMany(s(64,127),4,7,0),e.addMany([60,61,62,63],4,0,6),e.addMany(s(32,64),6,0,6),e.add(127,6,0,6),e.addMany(s(64,127),6,0,0),e.addMany(s(32,48),3,9,5),e.addMany(s(32,48),5,9,5),e.addMany(s(48,64),5,0,6),e.addMany(s(64,127),5,7,0),e.addMany(s(32,48),4,9,5),e.addMany(s(32,48),1,9,2),e.addMany(s(32,48),2,9,2),e.addMany(s(48,127),2,10,0),e.addMany(s(48,80),1,10,0),e.addMany(s(81,88),1,10,0),e.addMany([89,90,92],1,10,0),e.addMany(s(96,127),1,10,0),e.add(80,1,11,9),e.addMany(r,9,0,9),e.add(127,9,0,9),e.addMany(s(28,32),9,0,9),e.addMany(s(32,48),9,9,12),e.addMany(s(48,60),9,8,10),e.addMany([60,61,62,63],9,9,10),e.addMany(r,11,0,11),e.addMany(s(32,128),11,0,11),e.addMany(s(28,32),11,0,11),e.addMany(r,10,0,10),e.add(127,10,0,10),e.addMany(s(28,32),10,0,10),e.addMany(s(48,60),10,8,10),e.addMany([60,61,62,63],10,0,11),e.addMany(s(32,48),10,9,12),e.addMany(r,12,0,12),e.add(127,12,0,12),e.addMany(s(28,32),12,0,12),e.addMany(s(32,48),12,9,12),e.addMany(s(48,64),12,0,11),e.addMany(s(64,127),12,12,13),e.addMany(s(64,127),10,12,13),e.addMany(s(64,127),9,12,13),e.addMany(r,13,13,13),e.addMany(i,13,13,13),e.add(127,13,0,13),e.addMany([27,156,24,26],13,14,0),e.add(rh,0,2,0),e.add(rh,8,5,8),e.add(rh,6,0,6),e.add(rh,11,0,11),e.add(rh,13,13,13),e}(),oh=class extends Dr{constructor(e=nh){super(),this._transitions=e,this._parseStack={state:0,handlers:[],handlerPos:0,transition:0,chunkPos:0},this.initialState=0,this.currentState=this.initialState,this._params=new Gl,this._params.addParam(0),this._collect=0,this.precedingJoinState=0,this._printHandlerFb=(e,t,s)=>{},this._executeHandlerFb=e=>{},this._csiHandlerFb=(e,t)=>{},this._escHandlerFb=e=>{},this._errorHandlerFb=e=>e,this._printHandler=this._printHandlerFb,this._executeHandlers=Object.create(null),this._csiHandlers=Object.create(null),this._escHandlers=Object.create(null),this._register(Pr(()=>{this._csiHandlers=Object.create(null),this._executeHandlers=Object.create(null),this._escHandlers=Object.create(null)})),this._oscParser=this._register(new Jl),this._dcsParser=this._register(new eh),this._errorHandler=this._errorHandlerFb,this.registerEscHandler({final:"\\"},()=>!0)}_identifier(e,t=[64,126]){let s=0;if(e.prefix){if(e.prefix.length>1)throw new Error("only one byte as prefix supported");if(s=e.prefix.charCodeAt(0),s&&60>s||s>63)throw new Error("prefix must be in range 0x3c .. 0x3f")}if(e.intermediates){if(e.intermediates.length>2)throw new Error("only two bytes as intermediates are supported");for(let t=0;t<e.intermediates.length;++t){let i=e.intermediates.charCodeAt(t);if(32>i||i>47)throw new Error("intermediate must be in range 0x20 .. 0x2f");s<<=8,s|=i}}if(1!==e.final.length)throw new Error("final must be a single byte");let i=e.final.charCodeAt(0);if(t[0]>i||i>t[1])throw new Error(`final must be in range ${t[0]} .. ${t[1]}`);return s<<=8,s|=i,s}identToString(e){let t=[];for(;e;)t.push(String.fromCharCode(255&e)),e>>=8;return t.reverse().join("")}setPrintHandler(e){this._printHandler=e}clearPrintHandler(){this._printHandler=this._printHandlerFb}registerEscHandler(e,t){let s=this._identifier(e,[48,126]);void 0===this._escHandlers[s]&&(this._escHandlers[s]=[]);let i=this._escHandlers[s];return i.push(t),{dispose:()=>{let e=i.indexOf(t);-1!==e&&i.splice(e,1)}}}clearEscHandler(e){this._escHandlers[this._identifier(e,[48,126])]&&delete this._escHandlers[this._identifier(e,[48,126])]}setEscHandlerFallback(e){this._escHandlerFb=e}setExecuteHandler(e,t){this._executeHandlers[e.charCodeAt(0)]=t}clearExecuteHandler(e){this._executeHandlers[e.charCodeAt(0)]&&delete this._executeHandlers[e.charCodeAt(0)]}setExecuteHandlerFallback(e){this._executeHandlerFb=e}registerCsiHandler(e,t){let s=this._identifier(e);void 0===this._csiHandlers[s]&&(this._csiHandlers[s]=[]);let i=this._csiHandlers[s];return i.push(t),{dispose:()=>{let e=i.indexOf(t);-1!==e&&i.splice(e,1)}}}clearCsiHandler(e){this._csiHandlers[this._identifier(e)]&&delete this._csiHandlers[this._identifier(e)]}setCsiHandlerFallback(e){this._csiHandlerFb=e}registerDcsHandler(e,t){return this._dcsParser.registerHandler(this._identifier(e),t)}clearDcsHandler(e){this._dcsParser.clearHandler(this._identifier(e))}setDcsHandlerFallback(e){this._dcsParser.setHandlerFallback(e)}registerOscHandler(e,t){return this._oscParser.registerHandler(e,t)}clearOscHandler(e){this._oscParser.clearHandler(e)}setOscHandlerFallback(e){this._oscParser.setHandlerFallback(e)}setErrorHandler(e){this._errorHandler=e}clearErrorHandler(){this._errorHandler=this._errorHandlerFb}reset(){this.currentState=this.initialState,this._oscParser.reset(),this._dcsParser.reset(),this._params.reset(),this._params.addParam(0),this._collect=0,this.precedingJoinState=0,0!==this._parseStack.state&&(this._parseStack.state=2,this._parseStack.handlers=[])}_preserveStack(e,t,s,i,r){this._parseStack.state=e,this._parseStack.handlers=t,this._parseStack.handlerPos=s,this._parseStack.transition=i,this._parseStack.chunkPos=r}parse(e,t,s){let i,r=0,n=0,o=0;if(this._parseStack.state)if(2===this._parseStack.state)this._parseStack.state=0,o=this._parseStack.chunkPos+1;else{if(void 0===s||1===this._parseStack.state)throw this._parseStack.state=1,new Error("improper continuation due to previous async handler, giving up parsing");let t=this._parseStack.handlers,n=this._parseStack.handlerPos-1;switch(this._parseStack.state){case 3:if(!1===s&&n>-1)for(;n>=0&&(i=t[n](this._params),!0!==i);n--)if(i instanceof Promise)return this._parseStack.handlerPos=n,i;this._parseStack.handlers=[];break;case 4:if(!1===s&&n>-1)for(;n>=0&&(i=t[n](),!0!==i);n--)if(i instanceof Promise)return this._parseStack.handlerPos=n,i;this._parseStack.handlers=[];break;case 6:if(r=e[this._parseStack.chunkPos],i=this._dcsParser.unhook(24!==r&&26!==r,s),i)return i;27===r&&(this._parseStack.transition|=1),this._params.reset(),this._params.addParam(0),this._collect=0;break;case 5:if(r=e[this._parseStack.chunkPos],i=this._oscParser.end(24!==r&&26!==r,s),i)return i;27===r&&(this._parseStack.transition|=1),this._params.reset(),this._params.addParam(0),this._collect=0}this._parseStack.state=0,o=this._parseStack.chunkPos+1,this.precedingJoinState=0,this.currentState=15&this._parseStack.transition}for(let s=o;s<t;++s){switch(r=e[s],n=this._transitions.table[this.currentState<<8|(r<160?r:rh)],n>>4){case 2:for(let i=s+1;;++i){if(i>=t||(r=e[i])<32||r>126&&r<rh){this._printHandler(e,s,i),s=i-1;break}if(++i>=t||(r=e[i])<32||r>126&&r<rh){this._printHandler(e,s,i),s=i-1;break}if(++i>=t||(r=e[i])<32||r>126&&r<rh){this._printHandler(e,s,i),s=i-1;break}if(++i>=t||(r=e[i])<32||r>126&&r<rh){this._printHandler(e,s,i),s=i-1;break}}break;case 3:this._executeHandlers[r]?this._executeHandlers[r]():this._executeHandlerFb(r),this.precedingJoinState=0;break;case 0:break;case 1:if(this._errorHandler({position:s,code:r,currentState:this.currentState,collect:this._collect,params:this._params,abort:!1}).abort)return;break;case 7:let o=this._csiHandlers[this._collect<<8|r],a=o?o.length-1:-1;for(;a>=0&&(i=o[a](this._params),!0!==i);a--)if(i instanceof Promise)return this._preserveStack(3,o,a,n,s),i;a<0&&this._csiHandlerFb(this._collect<<8|r,this._params),this.precedingJoinState=0;break;case 8:do{switch(r){case 59:this._params.addParam(0);break;case 58:this._params.addSubParam(-1);break;default:this._params.addDigit(r-48)}}while(++s<t&&(r=e[s])>47&&r<60);s--;break;case 9:this._collect<<=8,this._collect|=r;break;case 10:let l=this._escHandlers[this._collect<<8|r],h=l?l.length-1:-1;for(;h>=0&&(i=l[h](),!0!==i);h--)if(i instanceof Promise)return this._preserveStack(4,l,h,n,s),i;h<0&&this._escHandlerFb(this._collect<<8|r),this.precedingJoinState=0;break;case 11:this._params.reset(),this._params.addParam(0),this._collect=0;break;case 12:this._dcsParser.hook(this._collect<<8|r,this._params);break;case 13:for(let i=s+1;;++i)if(i>=t||24===(r=e[i])||26===r||27===r||r>127&&r<rh){this._dcsParser.put(e,s,i),s=i-1;break}break;case 14:if(i=this._dcsParser.unhook(24!==r&&26!==r),i)return this._preserveStack(6,[],0,n,s),i;27===r&&(n|=1),this._params.reset(),this._params.addParam(0),this._collect=0,this.precedingJoinState=0;break;case 4:this._oscParser.start();break;case 5:for(let i=s+1;;i++)if(i>=t||(r=e[i])<32||r>127&&r<rh){this._oscParser.put(e,s,i),s=i-1;break}break;case 6:if(i=this._oscParser.end(24!==r&&26!==r),i)return this._preserveStack(5,[],0,n,s),i;27===r&&(n|=1),this._params.reset(),this._params.addParam(0),this._collect=0,this.precedingJoinState=0}this.currentState=15&n}}},ah=/^([\da-f])\/([\da-f])\/([\da-f])$|^([\da-f]{2})\/([\da-f]{2})\/([\da-f]{2})$|^([\da-f]{3})\/([\da-f]{3})\/([\da-f]{3})$|^([\da-f]{4})\/([\da-f]{4})\/([\da-f]{4})$/,lh=/^[\da-f]+$/;function hh(e){if(!e)return;let t=e.toLowerCase();if(0===t.indexOf("rgb:")){t=t.slice(4);let e=ah.exec(t);if(e){let t=e[1]?15:e[4]?255:e[7]?4095:65535;return[Math.round(parseInt(e[1]||e[4]||e[7]||e[10],16)/t*255),Math.round(parseInt(e[2]||e[5]||e[8]||e[11],16)/t*255),Math.round(parseInt(e[3]||e[6]||e[9]||e[12],16)/t*255)]}}else if(0===t.indexOf("#")&&(t=t.slice(1),lh.exec(t)&&[3,6,9,12].includes(t.length))){let e=t.length/3,s=[0,0,0];for(let i=0;i<3;++i){let r=parseInt(t.slice(e*i,e*i+e),16);s[i]=1===e?r<<4:2===e?r:3===e?r>>4:r>>8}return s}}function ch(e,t){let s=e.toString(16),i=s.length<2?"0"+s:s;switch(t){case 4:return s[0];case 8:return i;case 12:return(i+i).slice(0,3);default:return i+i}}function dh(e,t=16){let[s,i,r]=e;return`rgb:${ch(s,t)}/${ch(i,t)}/${ch(r,t)}`}var uh={"(":0,")":1,"*":2,"+":3,"-":1,".":2},ph=131072;function _h(e,t){if(e>24)return t.setWinLines||!1;switch(e){case 1:return!!t.restoreWin;case 2:return!!t.minimizeWin;case 3:return!!t.setWinPosition;case 4:return!!t.setWinSizePixels;case 5:return!!t.raiseWin;case 6:return!!t.lowerWin;case 7:return!!t.refreshWin;case 8:return!!t.setWinSizeChars;case 9:return!!t.maximizeWin;case 10:return!!t.fullscreenWin;case 11:return!!t.getWinState;case 13:return!!t.getWinPosition;case 14:return!!t.getWinSizePixels;case 15:return!!t.getScreenSizePixels;case 16:return!!t.getCellSizePixels;case 18:return!!t.getWinSizeChars;case 19:return!!t.getScreenSizeChars;case 20:return!!t.getIconTitle;case 21:return!!t.getWinTitle;case 22:return!!t.pushTitle;case 23:return!!t.popTitle;case 24:return!!t.setWinLines}return!1}var fh=0,gh=class extends Dr{constructor(e,t,s,i,r,n,o,a,l=new oh){super(),this._bufferService=e,this._charsetService=t,this._coreService=s,this._logService=i,this._optionsService=r,this._oscLinkService=n,this._coreMouseService=o,this._unicodeService=a,this._parser=l,this._parseBuffer=new Uint32Array(4096),this._stringDecoder=new Wi,this._utf8Decoder=new Ui,this._windowTitle="",this._iconName="",this._windowTitleStack=[],this._iconNameStack=[],this._curAttrData=gl.clone(),this._eraseAttrDataInternal=gl.clone(),this._onRequestBell=this._register(new Xr),this.onRequestBell=this._onRequestBell.event,this._onRequestRefreshRows=this._register(new Xr),this.onRequestRefreshRows=this._onRequestRefreshRows.event,this._onRequestReset=this._register(new Xr),this.onRequestReset=this._onRequestReset.event,this._onRequestSendFocus=this._register(new Xr),this.onRequestSendFocus=this._onRequestSendFocus.event,this._onRequestSyncScrollBar=this._register(new Xr),this.onRequestSyncScrollBar=this._onRequestSyncScrollBar.event,this._onRequestWindowsOptionsReport=this._register(new Xr),this.onRequestWindowsOptionsReport=this._onRequestWindowsOptionsReport.event,this._onA11yChar=this._register(new Xr),this.onA11yChar=this._onA11yChar.event,this._onA11yTab=this._register(new Xr),this.onA11yTab=this._onA11yTab.event,this._onCursorMove=this._register(new Xr),this.onCursorMove=this._onCursorMove.event,this._onLineFeed=this._register(new Xr),this.onLineFeed=this._onLineFeed.event,this._onScroll=this._register(new Xr),this.onScroll=this._onScroll.event,this._onTitleChange=this._register(new Xr),this.onTitleChange=this._onTitleChange.event,this._onColor=this._register(new Xr),this.onColor=this._onColor.event,this._parseStack={paused:!1,cursorStartX:0,cursorStartY:0,decodedLength:0,position:0},this._specialColors=[256,257,258],this._register(this._parser),this._dirtyRowTracker=new vh(this._bufferService),this._activeBuffer=this._bufferService.buffer,this._register(this._bufferService.buffers.onBufferActivate(e=>this._activeBuffer=e.activeBuffer)),this._parser.setCsiHandlerFallback((e,t)=>{this._logService.debug("Unknown CSI code: ",{identifier:this._parser.identToString(e),params:t.toArray()})}),this._parser.setEscHandlerFallback(e=>{this._logService.debug("Unknown ESC code: ",{identifier:this._parser.identToString(e)})}),this._parser.setExecuteHandlerFallback(e=>{this._logService.debug("Unknown EXECUTE code: ",{code:e})}),this._parser.setOscHandlerFallback((e,t,s)=>{this._logService.debug("Unknown OSC code: ",{identifier:e,action:t,data:s})}),this._parser.setDcsHandlerFallback((e,t,s)=>{"HOOK"===t&&(s=s.toArray()),this._logService.debug("Unknown DCS code: ",{identifier:this._parser.identToString(e),action:t,payload:s})}),this._parser.setPrintHandler((e,t,s)=>this.print(e,t,s)),this._parser.registerCsiHandler({final:"@"},e=>this.insertChars(e)),this._parser.registerCsiHandler({intermediates:" ",final:"@"},e=>this.scrollLeft(e)),this._parser.registerCsiHandler({final:"A"},e=>this.cursorUp(e)),this._parser.registerCsiHandler({intermediates:" ",final:"A"},e=>this.scrollRight(e)),this._parser.registerCsiHandler({final:"B"},e=>this.cursorDown(e)),this._parser.registerCsiHandler({final:"C"},e=>this.cursorForward(e)),this._parser.registerCsiHandler({final:"D"},e=>this.cursorBackward(e)),this._parser.registerCsiHandler({final:"E"},e=>this.cursorNextLine(e)),this._parser.registerCsiHandler({final:"F"},e=>this.cursorPrecedingLine(e)),this._parser.registerCsiHandler({final:"G"},e=>this.cursorCharAbsolute(e)),this._parser.registerCsiHandler({final:"H"},e=>this.cursorPosition(e)),this._parser.registerCsiHandler({final:"I"},e=>this.cursorForwardTab(e)),this._parser.registerCsiHandler({final:"J"},e=>this.eraseInDisplay(e,!1)),this._parser.registerCsiHandler({prefix:"?",final:"J"},e=>this.eraseInDisplay(e,!0)),this._parser.registerCsiHandler({final:"K"},e=>this.eraseInLine(e,!1)),this._parser.registerCsiHandler({prefix:"?",final:"K"},e=>this.eraseInLine(e,!0)),this._parser.registerCsiHandler({final:"L"},e=>this.insertLines(e)),this._parser.registerCsiHandler({final:"M"},e=>this.deleteLines(e)),this._parser.registerCsiHandler({final:"P"},e=>this.deleteChars(e)),this._parser.registerCsiHandler({final:"S"},e=>this.scrollUp(e)),this._parser.registerCsiHandler({final:"T"},e=>this.scrollDown(e)),this._parser.registerCsiHandler({final:"X"},e=>this.eraseChars(e)),this._parser.registerCsiHandler({final:"Z"},e=>this.cursorBackwardTab(e)),this._parser.registerCsiHandler({final:"`"},e=>this.charPosAbsolute(e)),this._parser.registerCsiHandler({final:"a"},e=>this.hPositionRelative(e)),this._parser.registerCsiHandler({final:"b"},e=>this.repeatPrecedingCharacter(e)),this._parser.registerCsiHandler({final:"c"},e=>this.sendDeviceAttributesPrimary(e)),this._parser.registerCsiHandler({prefix:">",final:"c"},e=>this.sendDeviceAttributesSecondary(e)),this._parser.registerCsiHandler({final:"d"},e=>this.linePosAbsolute(e)),this._parser.registerCsiHandler({final:"e"},e=>this.vPositionRelative(e)),this._parser.registerCsiHandler({final:"f"},e=>this.hVPosition(e)),this._parser.registerCsiHandler({final:"g"},e=>this.tabClear(e)),this._parser.registerCsiHandler({final:"h"},e=>this.setMode(e)),this._parser.registerCsiHandler({prefix:"?",final:"h"},e=>this.setModePrivate(e)),this._parser.registerCsiHandler({final:"l"},e=>this.resetMode(e)),this._parser.registerCsiHandler({prefix:"?",final:"l"},e=>this.resetModePrivate(e)),this._parser.registerCsiHandler({final:"m"},e=>this.charAttributes(e)),this._parser.registerCsiHandler({final:"n"},e=>this.deviceStatus(e)),this._parser.registerCsiHandler({prefix:"?",final:"n"},e=>this.deviceStatusPrivate(e)),this._parser.registerCsiHandler({intermediates:"!",final:"p"},e=>this.softReset(e)),this._parser.registerCsiHandler({intermediates:" ",final:"q"},e=>this.setCursorStyle(e)),this._parser.registerCsiHandler({final:"r"},e=>this.setScrollRegion(e)),this._parser.registerCsiHandler({final:"s"},e=>this.saveCursor(e)),this._parser.registerCsiHandler({final:"t"},e=>this.windowOptions(e)),this._parser.registerCsiHandler({final:"u"},e=>this.restoreCursor(e)),this._parser.registerCsiHandler({intermediates:"'",final:"}"},e=>this.insertColumns(e)),this._parser.registerCsiHandler({intermediates:"'",final:"~"},e=>this.deleteColumns(e)),this._parser.registerCsiHandler({intermediates:'"',final:"q"},e=>this.selectProtected(e)),this._parser.registerCsiHandler({intermediates:"$",final:"p"},e=>this.requestMode(e,!0)),this._parser.registerCsiHandler({prefix:"?",intermediates:"$",final:"p"},e=>this.requestMode(e,!1)),this._parser.setExecuteHandler(Lo.BEL,()=>this.bell()),this._parser.setExecuteHandler(Lo.LF,()=>this.lineFeed()),this._parser.setExecuteHandler(Lo.VT,()=>this.lineFeed()),this._parser.setExecuteHandler(Lo.FF,()=>this.lineFeed()),this._parser.setExecuteHandler(Lo.CR,()=>this.carriageReturn()),this._parser.setExecuteHandler(Lo.BS,()=>this.backspace()),this._parser.setExecuteHandler(Lo.HT,()=>this.tab()),this._parser.setExecuteHandler(Lo.SO,()=>this.shiftOut()),this._parser.setExecuteHandler(Lo.SI,()=>this.shiftIn()),this._parser.setExecuteHandler(Mo.IND,()=>this.index()),this._parser.setExecuteHandler(Mo.NEL,()=>this.nextLine()),this._parser.setExecuteHandler(Mo.HTS,()=>this.tabSet()),this._parser.registerOscHandler(0,new Zl(e=>(this.setTitle(e),this.setIconName(e),!0))),this._parser.registerOscHandler(1,new Zl(e=>this.setIconName(e))),this._parser.registerOscHandler(2,new Zl(e=>this.setTitle(e))),this._parser.registerOscHandler(4,new Zl(e=>this.setOrReportIndexedColor(e))),this._parser.registerOscHandler(8,new Zl(e=>this.setHyperlink(e))),this._parser.registerOscHandler(10,new Zl(e=>this.setOrReportFgColor(e))),this._parser.registerOscHandler(11,new Zl(e=>this.setOrReportBgColor(e))),this._parser.registerOscHandler(12,new Zl(e=>this.setOrReportCursorColor(e))),this._parser.registerOscHandler(104,new Zl(e=>this.restoreIndexedColor(e))),this._parser.registerOscHandler(110,new Zl(e=>this.restoreFgColor(e))),this._parser.registerOscHandler(111,new Zl(e=>this.restoreBgColor(e))),this._parser.registerOscHandler(112,new Zl(e=>this.restoreCursorColor(e))),this._parser.registerEscHandler({final:"7"},()=>this.saveCursor()),this._parser.registerEscHandler({final:"8"},()=>this.restoreCursor()),this._parser.registerEscHandler({final:"D"},()=>this.index()),this._parser.registerEscHandler({final:"E"},()=>this.nextLine()),this._parser.registerEscHandler({final:"H"},()=>this.tabSet()),this._parser.registerEscHandler({final:"M"},()=>this.reverseIndex()),this._parser.registerEscHandler({final:"="},()=>this.keypadApplicationMode()),this._parser.registerEscHandler({final:">"},()=>this.keypadNumericMode()),this._parser.registerEscHandler({final:"c"},()=>this.fullReset()),this._parser.registerEscHandler({final:"n"},()=>this.setgLevel(2)),this._parser.registerEscHandler({final:"o"},()=>this.setgLevel(3)),this._parser.registerEscHandler({final:"|"},()=>this.setgLevel(3)),this._parser.registerEscHandler({final:"}"},()=>this.setgLevel(2)),this._parser.registerEscHandler({final:"~"},()=>this.setgLevel(1)),this._parser.registerEscHandler({intermediates:"%",final:"@"},()=>this.selectDefaultCharset()),this._parser.registerEscHandler({intermediates:"%",final:"G"},()=>this.selectDefaultCharset());for(let e in xl)this._parser.registerEscHandler({intermediates:"(",final:e},()=>this.selectCharset("("+e)),this._parser.registerEscHandler({intermediates:")",final:e},()=>this.selectCharset(")"+e)),this._parser.registerEscHandler({intermediates:"*",final:e},()=>this.selectCharset("*"+e)),this._parser.registerEscHandler({intermediates:"+",final:e},()=>this.selectCharset("+"+e)),this._parser.registerEscHandler({intermediates:"-",final:e},()=>this.selectCharset("-"+e)),this._parser.registerEscHandler({intermediates:".",final:e},()=>this.selectCharset("."+e)),this._parser.registerEscHandler({intermediates:"/",final:e},()=>this.selectCharset("/"+e));this._parser.registerEscHandler({intermediates:"#",final:"8"},()=>this.screenAlignmentPattern()),this._parser.setErrorHandler(e=>(this._logService.error("Parsing error: ",e),e)),this._parser.registerDcsHandler({intermediates:"$",final:"q"},new sh((e,t)=>this.requestStatusString(e,t)))}getAttrData(){return this._curAttrData}_preserveStack(e,t,s,i){this._parseStack.paused=!0,this._parseStack.cursorStartX=e,this._parseStack.cursorStartY=t,this._parseStack.decodedLength=s,this._parseStack.position=i}_logSlowResolvingAsync(e){this._logService.logLevel<=3&&Promise.race([e,new Promise((e,t)=>setTimeout(()=>t("#SLOW_TIMEOUT"),5e3))]).catch(e=>{if("#SLOW_TIMEOUT"!==e)throw e;console.warn("async parser handler taking longer than 5000 ms")})}_getCurrentLinkId(){return this._curAttrData.extended.urlId}parse(e,t){let s,i=this._activeBuffer.x,r=this._activeBuffer.y,n=0,o=this._parseStack.paused;if(o){if(s=this._parser.parse(this._parseBuffer,this._parseStack.decodedLength,t))return this._logSlowResolvingAsync(s),s;i=this._parseStack.cursorStartX,r=this._parseStack.cursorStartY,this._parseStack.paused=!1,e.length>ph&&(n=this._parseStack.position+ph)}if(this._logService.logLevel<=1&&this._logService.debug("parsing data "+("string"==typeof e?` "${e}"`:` "${Array.prototype.map.call(e,e=>String.fromCharCode(e)).join("")}"`)),0===this._logService.logLevel&&this._logService.trace("parsing data (codes)","string"==typeof e?e.split("").map(e=>e.charCodeAt(0)):e),this._parseBuffer.length<e.length&&this._parseBuffer.length<ph&&(this._parseBuffer=new Uint32Array(Math.min(e.length,ph))),o||this._dirtyRowTracker.clearRange(),e.length>ph)for(let t=n;t<e.length;t+=ph){let n=t+ph<e.length?t+ph:e.length,o="string"==typeof e?this._stringDecoder.decode(e.substring(t,n),this._parseBuffer):this._utf8Decoder.decode(e.subarray(t,n),this._parseBuffer);if(s=this._parser.parse(this._parseBuffer,o))return this._preserveStack(i,r,o,t),this._logSlowResolvingAsync(s),s}else if(!o){let t="string"==typeof e?this._stringDecoder.decode(e,this._parseBuffer):this._utf8Decoder.decode(e,this._parseBuffer);if(s=this._parser.parse(this._parseBuffer,t))return this._preserveStack(i,r,t,0),this._logSlowResolvingAsync(s),s}(this._activeBuffer.x!==i||this._activeBuffer.y!==r)&&this._onCursorMove.fire();let a=this._dirtyRowTracker.end+(this._bufferService.buffer.ybase-this._bufferService.buffer.ydisp),l=this._dirtyRowTracker.start+(this._bufferService.buffer.ybase-this._bufferService.buffer.ydisp);l<this._bufferService.rows&&this._onRequestRefreshRows.fire({start:Math.min(l,this._bufferService.rows-1),end:Math.min(a,this._bufferService.rows-1)})}print(e,t,s){let i,r,n=this._charsetService.charset,o=this._optionsService.rawOptions.screenReaderMode,a=this._bufferService.cols,l=this._coreService.decPrivateModes.wraparound,h=this._coreService.modes.insertMode,c=this._curAttrData,d=this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y);this._dirtyRowTracker.markDirty(this._activeBuffer.y),this._activeBuffer.x&&s-t>0&&2===d.getWidth(this._activeBuffer.x-1)&&d.setCellFromCodepoint(this._activeBuffer.x-1,0,1,c);let u=this._parser.precedingJoinState;for(let p=t;p<s;++p){if(i=e[p],i<127&&n){let e=n[String.fromCharCode(i)];e&&(i=e.charCodeAt(0))}let t=this._unicodeService.charProperties(i,u);r=Vl.extractWidth(t);let s=Vl.extractShouldJoin(t),_=s?Vl.extractWidth(u):0;if(u=t,o&&this._onA11yChar.fire(Fi(i)),this._getCurrentLinkId()&&this._oscLinkService.addLineToLink(this._getCurrentLinkId(),this._activeBuffer.ybase+this._activeBuffer.y),this._activeBuffer.x+r-_>a)if(l){let e=d,t=this._activeBuffer.x-_;for(this._activeBuffer.x=_,this._activeBuffer.y++,this._activeBuffer.y===this._activeBuffer.scrollBottom+1?(this._activeBuffer.y--,this._bufferService.scroll(this._eraseAttrData(),!0)):(this._activeBuffer.y>=this._bufferService.rows&&(this._activeBuffer.y=this._bufferService.rows-1),this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y).isWrapped=!0),d=this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y),_>0&&d instanceof ml&&d.copyCellsFrom(e,t,0,_,!1);t<a;)e.setCellFromCodepoint(t++,0,1,c)}else if(this._activeBuffer.x=a-1,2===r)continue;if(s&&this._activeBuffer.x){let e=d.getWidth(this._activeBuffer.x-1)?1:2;d.addCodepointToCell(this._activeBuffer.x-e,i,r);for(let e=r-_;--e>=0;)d.setCellFromCodepoint(this._activeBuffer.x++,0,0,c);continue}if(h&&(d.insertCells(this._activeBuffer.x,r-_,this._activeBuffer.getNullCell(c)),2===d.getWidth(a-1)&&d.setCellFromCodepoint(a-1,0,1,c)),d.setCellFromCodepoint(this._activeBuffer.x++,i,r,c),r>0)for(;--r;)d.setCellFromCodepoint(this._activeBuffer.x++,0,0,c)}this._parser.precedingJoinState=u,this._activeBuffer.x<a&&s-t>0&&0===d.getWidth(this._activeBuffer.x)&&!d.hasContent(this._activeBuffer.x)&&d.setCellFromCodepoint(this._activeBuffer.x,0,1,c),this._dirtyRowTracker.markDirty(this._activeBuffer.y)}registerCsiHandler(e,t){return"t"!==e.final||e.prefix||e.intermediates?this._parser.registerCsiHandler(e,t):this._parser.registerCsiHandler(e,e=>!_h(e.params[0],this._optionsService.rawOptions.windowOptions)||t(e))}registerDcsHandler(e,t){return this._parser.registerDcsHandler(e,new sh(t))}registerEscHandler(e,t){return this._parser.registerEscHandler(e,t)}registerOscHandler(e,t){return this._parser.registerOscHandler(e,new Zl(t))}bell(){return this._onRequestBell.fire(),!0}lineFeed(){return this._dirtyRowTracker.markDirty(this._activeBuffer.y),this._optionsService.rawOptions.convertEol&&(this._activeBuffer.x=0),this._activeBuffer.y++,this._activeBuffer.y===this._activeBuffer.scrollBottom+1?(this._activeBuffer.y--,this._bufferService.scroll(this._eraseAttrData())):this._activeBuffer.y>=this._bufferService.rows?this._activeBuffer.y=this._bufferService.rows-1:this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y).isWrapped=!1,this._activeBuffer.x>=this._bufferService.cols&&this._activeBuffer.x--,this._dirtyRowTracker.markDirty(this._activeBuffer.y),this._onLineFeed.fire(),!0}carriageReturn(){return this._activeBuffer.x=0,!0}backspace(){if(!this._coreService.decPrivateModes.reverseWraparound)return this._restrictCursor(),this._activeBuffer.x>0&&this._activeBuffer.x--,!0;if(this._restrictCursor(this._bufferService.cols),this._activeBuffer.x>0)this._activeBuffer.x--;else if(0===this._activeBuffer.x&&this._activeBuffer.y>this._activeBuffer.scrollTop&&this._activeBuffer.y<=this._activeBuffer.scrollBottom&&this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y)?.isWrapped){this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y).isWrapped=!1,this._activeBuffer.y--,this._activeBuffer.x=this._bufferService.cols-1;let e=this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y);e.hasWidth(this._activeBuffer.x)&&!e.hasContent(this._activeBuffer.x)&&this._activeBuffer.x--}return this._restrictCursor(),!0}tab(){if(this._activeBuffer.x>=this._bufferService.cols)return!0;let e=this._activeBuffer.x;return this._activeBuffer.x=this._activeBuffer.nextStop(),this._optionsService.rawOptions.screenReaderMode&&this._onA11yTab.fire(this._activeBuffer.x-e),!0}shiftOut(){return this._charsetService.setgLevel(1),!0}shiftIn(){return this._charsetService.setgLevel(0),!0}_restrictCursor(e=this._bufferService.cols-1){this._activeBuffer.x=Math.min(e,Math.max(0,this._activeBuffer.x)),this._activeBuffer.y=this._coreService.decPrivateModes.origin?Math.min(this._activeBuffer.scrollBottom,Math.max(this._activeBuffer.scrollTop,this._activeBuffer.y)):Math.min(this._bufferService.rows-1,Math.max(0,this._activeBuffer.y)),this._dirtyRowTracker.markDirty(this._activeBuffer.y)}_setCursor(e,t){this._dirtyRowTracker.markDirty(this._activeBuffer.y),this._coreService.decPrivateModes.origin?(this._activeBuffer.x=e,this._activeBuffer.y=this._activeBuffer.scrollTop+t):(this._activeBuffer.x=e,this._activeBuffer.y=t),this._restrictCursor(),this._dirtyRowTracker.markDirty(this._activeBuffer.y)}_moveCursor(e,t){this._restrictCursor(),this._setCursor(this._activeBuffer.x+e,this._activeBuffer.y+t)}cursorUp(e){let t=this._activeBuffer.y-this._activeBuffer.scrollTop;return t>=0?this._moveCursor(0,-Math.min(t,e.params[0]||1)):this._moveCursor(0,-(e.params[0]||1)),!0}cursorDown(e){let t=this._activeBuffer.scrollBottom-this._activeBuffer.y;return t>=0?this._moveCursor(0,Math.min(t,e.params[0]||1)):this._moveCursor(0,e.params[0]||1),!0}cursorForward(e){return this._moveCursor(e.params[0]||1,0),!0}cursorBackward(e){return this._moveCursor(-(e.params[0]||1),0),!0}cursorNextLine(e){return this.cursorDown(e),this._activeBuffer.x=0,!0}cursorPrecedingLine(e){return this.cursorUp(e),this._activeBuffer.x=0,!0}cursorCharAbsolute(e){return this._setCursor((e.params[0]||1)-1,this._activeBuffer.y),!0}cursorPosition(e){return this._setCursor(e.length>=2?(e.params[1]||1)-1:0,(e.params[0]||1)-1),!0}charPosAbsolute(e){return this._setCursor((e.params[0]||1)-1,this._activeBuffer.y),!0}hPositionRelative(e){return this._moveCursor(e.params[0]||1,0),!0}linePosAbsolute(e){return this._setCursor(this._activeBuffer.x,(e.params[0]||1)-1),!0}vPositionRelative(e){return this._moveCursor(0,e.params[0]||1),!0}hVPosition(e){return this.cursorPosition(e),!0}tabClear(e){let t=e.params[0];return 0===t?delete this._activeBuffer.tabs[this._activeBuffer.x]:3===t&&(this._activeBuffer.tabs={}),!0}cursorForwardTab(e){if(this._activeBuffer.x>=this._bufferService.cols)return!0;let t=e.params[0]||1;for(;t--;)this._activeBuffer.x=this._activeBuffer.nextStop();return!0}cursorBackwardTab(e){if(this._activeBuffer.x>=this._bufferService.cols)return!0;let t=e.params[0]||1;for(;t--;)this._activeBuffer.x=this._activeBuffer.prevStop();return!0}selectProtected(e){let t=e.params[0];return 1===t&&(this._curAttrData.bg|=536870912),(2===t||0===t)&&(this._curAttrData.bg&=-536870913),!0}_eraseInBufferLine(e,t,s,i=!1,r=!1){let n=this._activeBuffer.lines.get(this._activeBuffer.ybase+e);n.replaceCells(t,s,this._activeBuffer.getNullCell(this._eraseAttrData()),r),i&&(n.isWrapped=!1)}_resetBufferLine(e,t=!1){let s=this._activeBuffer.lines.get(this._activeBuffer.ybase+e);s&&(s.fill(this._activeBuffer.getNullCell(this._eraseAttrData()),t),this._bufferService.buffer.clearMarkers(this._activeBuffer.ybase+e),s.isWrapped=!1)}eraseInDisplay(e,t=!1){let s;switch(this._restrictCursor(this._bufferService.cols),e.params[0]){case 0:for(s=this._activeBuffer.y,this._dirtyRowTracker.markDirty(s),this._eraseInBufferLine(s++,this._activeBuffer.x,this._bufferService.cols,0===this._activeBuffer.x,t);s<this._bufferService.rows;s++)this._resetBufferLine(s,t);this._dirtyRowTracker.markDirty(s);break;case 1:for(s=this._activeBuffer.y,this._dirtyRowTracker.markDirty(s),this._eraseInBufferLine(s,0,this._activeBuffer.x+1,!0,t),this._activeBuffer.x+1>=this._bufferService.cols&&(this._activeBuffer.lines.get(s+1).isWrapped=!1);s--;)this._resetBufferLine(s,t);this._dirtyRowTracker.markDirty(0);break;case 2:if(this._optionsService.rawOptions.scrollOnEraseInDisplay){for(s=this._bufferService.rows,this._dirtyRowTracker.markRangeDirty(0,s-1);s--&&!this._activeBuffer.lines.get(this._activeBuffer.ybase+s)?.getTrimmedLength(););for(;s>=0;s--)this._bufferService.scroll(this._eraseAttrData())}else{for(s=this._bufferService.rows,this._dirtyRowTracker.markDirty(s-1);s--;)this._resetBufferLine(s,t);this._dirtyRowTracker.markDirty(0)}break;case 3:let e=this._activeBuffer.lines.length-this._bufferService.rows;e>0&&(this._activeBuffer.lines.trimStart(e),this._activeBuffer.ybase=Math.max(this._activeBuffer.ybase-e,0),this._activeBuffer.ydisp=Math.max(this._activeBuffer.ydisp-e,0),this._onScroll.fire(0))}return!0}eraseInLine(e,t=!1){switch(this._restrictCursor(this._bufferService.cols),e.params[0]){case 0:this._eraseInBufferLine(this._activeBuffer.y,this._activeBuffer.x,this._bufferService.cols,0===this._activeBuffer.x,t);break;case 1:this._eraseInBufferLine(this._activeBuffer.y,0,this._activeBuffer.x+1,!1,t);break;case 2:this._eraseInBufferLine(this._activeBuffer.y,0,this._bufferService.cols,!0,t)}return this._dirtyRowTracker.markDirty(this._activeBuffer.y),!0}insertLines(e){this._restrictCursor();let t=e.params[0]||1;if(this._activeBuffer.y>this._activeBuffer.scrollBottom||this._activeBuffer.y<this._activeBuffer.scrollTop)return!0;let s=this._activeBuffer.ybase+this._activeBuffer.y,i=this._bufferService.rows-1-this._activeBuffer.scrollBottom,r=this._bufferService.rows-1+this._activeBuffer.ybase-i+1;for(;t--;)this._activeBuffer.lines.splice(r-1,1),this._activeBuffer.lines.splice(s,0,this._activeBuffer.getBlankLine(this._eraseAttrData()));return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.y,this._activeBuffer.scrollBottom),this._activeBuffer.x=0,!0}deleteLines(e){this._restrictCursor();let t=e.params[0]||1;if(this._activeBuffer.y>this._activeBuffer.scrollBottom||this._activeBuffer.y<this._activeBuffer.scrollTop)return!0;let s,i=this._activeBuffer.ybase+this._activeBuffer.y;for(s=this._bufferService.rows-1-this._activeBuffer.scrollBottom,s=this._bufferService.rows-1+this._activeBuffer.ybase-s;t--;)this._activeBuffer.lines.splice(i,1),this._activeBuffer.lines.splice(s,0,this._activeBuffer.getBlankLine(this._eraseAttrData()));return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.y,this._activeBuffer.scrollBottom),this._activeBuffer.x=0,!0}insertChars(e){this._restrictCursor();let t=this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y);return t&&(t.insertCells(this._activeBuffer.x,e.params[0]||1,this._activeBuffer.getNullCell(this._eraseAttrData())),this._dirtyRowTracker.markDirty(this._activeBuffer.y)),!0}deleteChars(e){this._restrictCursor();let t=this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y);return t&&(t.deleteCells(this._activeBuffer.x,e.params[0]||1,this._activeBuffer.getNullCell(this._eraseAttrData())),this._dirtyRowTracker.markDirty(this._activeBuffer.y)),!0}scrollUp(e){let t=e.params[0]||1;for(;t--;)this._activeBuffer.lines.splice(this._activeBuffer.ybase+this._activeBuffer.scrollTop,1),this._activeBuffer.lines.splice(this._activeBuffer.ybase+this._activeBuffer.scrollBottom,0,this._activeBuffer.getBlankLine(this._eraseAttrData()));return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.scrollTop,this._activeBuffer.scrollBottom),!0}scrollDown(e){let t=e.params[0]||1;for(;t--;)this._activeBuffer.lines.splice(this._activeBuffer.ybase+this._activeBuffer.scrollBottom,1),this._activeBuffer.lines.splice(this._activeBuffer.ybase+this._activeBuffer.scrollTop,0,this._activeBuffer.getBlankLine(gl));return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.scrollTop,this._activeBuffer.scrollBottom),!0}scrollLeft(e){if(this._activeBuffer.y>this._activeBuffer.scrollBottom||this._activeBuffer.y<this._activeBuffer.scrollTop)return!0;let t=e.params[0]||1;for(let e=this._activeBuffer.scrollTop;e<=this._activeBuffer.scrollBottom;++e){let s=this._activeBuffer.lines.get(this._activeBuffer.ybase+e);s.deleteCells(0,t,this._activeBuffer.getNullCell(this._eraseAttrData())),s.isWrapped=!1}return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.scrollTop,this._activeBuffer.scrollBottom),!0}scrollRight(e){if(this._activeBuffer.y>this._activeBuffer.scrollBottom||this._activeBuffer.y<this._activeBuffer.scrollTop)return!0;let t=e.params[0]||1;for(let e=this._activeBuffer.scrollTop;e<=this._activeBuffer.scrollBottom;++e){let s=this._activeBuffer.lines.get(this._activeBuffer.ybase+e);s.insertCells(0,t,this._activeBuffer.getNullCell(this._eraseAttrData())),s.isWrapped=!1}return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.scrollTop,this._activeBuffer.scrollBottom),!0}insertColumns(e){if(this._activeBuffer.y>this._activeBuffer.scrollBottom||this._activeBuffer.y<this._activeBuffer.scrollTop)return!0;let t=e.params[0]||1;for(let e=this._activeBuffer.scrollTop;e<=this._activeBuffer.scrollBottom;++e){let s=this._activeBuffer.lines.get(this._activeBuffer.ybase+e);s.insertCells(this._activeBuffer.x,t,this._activeBuffer.getNullCell(this._eraseAttrData())),s.isWrapped=!1}return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.scrollTop,this._activeBuffer.scrollBottom),!0}deleteColumns(e){if(this._activeBuffer.y>this._activeBuffer.scrollBottom||this._activeBuffer.y<this._activeBuffer.scrollTop)return!0;let t=e.params[0]||1;for(let e=this._activeBuffer.scrollTop;e<=this._activeBuffer.scrollBottom;++e){let s=this._activeBuffer.lines.get(this._activeBuffer.ybase+e);s.deleteCells(this._activeBuffer.x,t,this._activeBuffer.getNullCell(this._eraseAttrData())),s.isWrapped=!1}return this._dirtyRowTracker.markRangeDirty(this._activeBuffer.scrollTop,this._activeBuffer.scrollBottom),!0}eraseChars(e){this._restrictCursor();let t=this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y);return t&&(t.replaceCells(this._activeBuffer.x,this._activeBuffer.x+(e.params[0]||1),this._activeBuffer.getNullCell(this._eraseAttrData())),this._dirtyRowTracker.markDirty(this._activeBuffer.y)),!0}repeatPrecedingCharacter(e){let t=this._parser.precedingJoinState;if(!t)return!0;let s=e.params[0]||1,i=Vl.extractWidth(t),r=this._activeBuffer.x-i,n=this._activeBuffer.lines.get(this._activeBuffer.ybase+this._activeBuffer.y).getString(r),o=new Uint32Array(n.length*s),a=0;for(let e=0;e<n.length;){let t=n.codePointAt(e)||0;o[a++]=t,e+=t>65535?2:1}let l=a;for(let e=1;e<s;++e)o.copyWithin(l,0,a),l+=a;return this.print(o,0,l),!0}sendDeviceAttributesPrimary(e){return e.params[0]>0||(this._is("xterm")||this._is("rxvt-unicode")||this._is("screen")?this._coreService.triggerDataEvent(Lo.ESC+"[?1;2c"):this._is("linux")&&this._coreService.triggerDataEvent(Lo.ESC+"[?6c")),!0}sendDeviceAttributesSecondary(e){return e.params[0]>0||(this._is("xterm")?this._coreService.triggerDataEvent(Lo.ESC+"[>0;276;0c"):this._is("rxvt-unicode")?this._coreService.triggerDataEvent(Lo.ESC+"[>85;95;0c"):this._is("linux")?this._coreService.triggerDataEvent(e.params[0]+"c"):this._is("screen")&&this._coreService.triggerDataEvent(Lo.ESC+"[>83;40003;0c")),!0}_is(e){return 0===(this._optionsService.rawOptions.termName+"").indexOf(e)}setMode(e){for(let t=0;t<e.length;t++)switch(e.params[t]){case 4:this._coreService.modes.insertMode=!0;break;case 20:this._optionsService.options.convertEol=!0}return!0}setModePrivate(e){for(let t=0;t<e.length;t++)switch(e.params[t]){case 1:this._coreService.decPrivateModes.applicationCursorKeys=!0;break;case 2:this._charsetService.setgCharset(0,$l),this._charsetService.setgCharset(1,$l),this._charsetService.setgCharset(2,$l),this._charsetService.setgCharset(3,$l);break;case 3:this._optionsService.rawOptions.windowOptions.setWinLines&&(this._bufferService.resize(132,this._bufferService.rows),this._onRequestReset.fire());break;case 6:this._coreService.decPrivateModes.origin=!0,this._setCursor(0,0);break;case 7:this._coreService.decPrivateModes.wraparound=!0;break;case 12:this._optionsService.options.cursorBlink=!0;break;case 45:this._coreService.decPrivateModes.reverseWraparound=!0;break;case 66:this._logService.debug("Serial port requested application keypad."),this._coreService.decPrivateModes.applicationKeypad=!0,this._onRequestSyncScrollBar.fire();break;case 9:this._coreMouseService.activeProtocol="X10";break;case 1e3:this._coreMouseService.activeProtocol="VT200";break;case 1002:this._coreMouseService.activeProtocol="DRAG";break;case 1003:this._coreMouseService.activeProtocol="ANY";break;case 1004:this._coreService.decPrivateModes.sendFocus=!0,this._onRequestSendFocus.fire();break;case 1005:this._logService.debug("DECSET 1005 not supported (see #2507)");break;case 1006:this._coreMouseService.activeEncoding="SGR";break;case 1015:this._logService.debug("DECSET 1015 not supported (see #2507)");break;case 1016:this._coreMouseService.activeEncoding="SGR_PIXELS";break;case 25:this._coreService.isCursorHidden=!1;break;case 1048:this.saveCursor();break;case 1049:this.saveCursor();case 47:case 1047:this._bufferService.buffers.activateAltBuffer(this._eraseAttrData()),this._coreService.isCursorInitialized=!0,this._onRequestRefreshRows.fire(void 0),this._onRequestSyncScrollBar.fire();break;case 2004:this._coreService.decPrivateModes.bracketedPasteMode=!0;break;case 2026:this._coreService.decPrivateModes.synchronizedOutput=!0}return!0}resetMode(e){for(let t=0;t<e.length;t++)switch(e.params[t]){case 4:this._coreService.modes.insertMode=!1;break;case 20:this._optionsService.options.convertEol=!1}return!0}resetModePrivate(e){for(let t=0;t<e.length;t++)switch(e.params[t]){case 1:this._coreService.decPrivateModes.applicationCursorKeys=!1;break;case 3:this._optionsService.rawOptions.windowOptions.setWinLines&&(this._bufferService.resize(80,this._bufferService.rows),this._onRequestReset.fire());break;case 6:this._coreService.decPrivateModes.origin=!1,this._setCursor(0,0);break;case 7:this._coreService.decPrivateModes.wraparound=!1;break;case 12:this._optionsService.options.cursorBlink=!1;break;case 45:this._coreService.decPrivateModes.reverseWraparound=!1;break;case 66:this._logService.debug("Switching back to normal keypad."),this._coreService.decPrivateModes.applicationKeypad=!1,this._onRequestSyncScrollBar.fire();break;case 9:case 1e3:case 1002:case 1003:this._coreMouseService.activeProtocol="NONE";break;case 1004:this._coreService.decPrivateModes.sendFocus=!1;break;case 1005:this._logService.debug("DECRST 1005 not supported (see #2507)");break;case 1006:case 1016:this._coreMouseService.activeEncoding="DEFAULT";break;case 1015:this._logService.debug("DECRST 1015 not supported (see #2507)");break;case 25:this._coreService.isCursorHidden=!0;break;case 1048:this.restoreCursor();break;case 1049:case 47:case 1047:this._bufferService.buffers.activateNormalBuffer(),1049===e.params[t]&&this.restoreCursor(),this._coreService.isCursorInitialized=!0,this._onRequestRefreshRows.fire(void 0),this._onRequestSyncScrollBar.fire();break;case 2004:this._coreService.decPrivateModes.bracketedPasteMode=!1;break;case 2026:this._coreService.decPrivateModes.synchronizedOutput=!1,this._onRequestRefreshRows.fire(void 0)}return!0}requestMode(e,t){let s;(e=>{e[e.NOT_RECOGNIZED=0]="NOT_RECOGNIZED",e[e.SET=1]="SET",e[e.RESET=2]="RESET",e[e.PERMANENTLY_SET=3]="PERMANENTLY_SET",e[e.PERMANENTLY_RESET=4]="PERMANENTLY_RESET"})(s||={});let i=this._coreService.decPrivateModes,{activeProtocol:r,activeEncoding:n}=this._coreMouseService,o=this._coreService,{buffers:a,cols:l}=this._bufferService,{active:h,alt:c}=a,d=this._optionsService.rawOptions,u=(e,s)=>(o.triggerDataEvent(`${Lo.ESC}[${t?"":"?"}${e};${s}$y`),!0),p=e=>e?1:2,_=e.params[0];return u(_,t?2===_?4:4===_?p(o.modes.insertMode):12===_?3:20===_?p(d.convertEol):0:1===_?p(i.applicationCursorKeys):3===_?d.windowOptions.setWinLines?80===l?2:132===l?1:0:0:6===_?p(i.origin):7===_?p(i.wraparound):8===_?3:9===_?p("X10"===r):12===_?p(d.cursorBlink):25===_?p(!o.isCursorHidden):45===_?p(i.reverseWraparound):66===_?p(i.applicationKeypad):67===_?4:1e3===_?p("VT200"===r):1002===_?p("DRAG"===r):1003===_?p("ANY"===r):1004===_?p(i.sendFocus):1005===_?4:1006===_?p("SGR"===n):1015===_?4:1016===_?p("SGR_PIXELS"===n):1048===_?1:47===_||1047===_||1049===_?p(h===c):2004===_?p(i.bracketedPasteMode):2026===_?p(i.synchronizedOutput):0)}_updateAttrColor(e,t,s,i,r){return 2===t?(e|=50331648,e&=-16777216,e|=Vi.fromColorRGB([s,i,r])):5===t&&(e&=-50331904,e|=33554432|255&s),e}_extractColor(e,t,s){let i=[0,0,-1,0,0,0],r=0,n=0;do{if(i[n+r]=e.params[t+n],e.hasSubParams(t+n)){let s=e.getSubParams(t+n),o=0;do{5===i[1]&&(r=1),i[n+o+1+r]=s[o]}while(++o<s.length&&o+n+1+r<i.length);break}if(5===i[1]&&n+r>=2||2===i[1]&&n+r>=5)break;i[1]&&(r=1)}while(++n+t<e.length&&n+r<i.length);for(let e=2;e<i.length;++e)-1===i[e]&&(i[e]=0);switch(i[0]){case 38:s.fg=this._updateAttrColor(s.fg,i[1],i[3],i[4],i[5]);break;case 48:s.bg=this._updateAttrColor(s.bg,i[1],i[3],i[4],i[5]);break;case 58:s.extended=s.extended.clone(),s.extended.underlineColor=this._updateAttrColor(s.extended.underlineColor,i[1],i[3],i[4],i[5])}return n}_processUnderline(e,t){t.extended=t.extended.clone(),(!~e||e>5)&&(e=1),t.extended.underlineStyle=e,t.fg|=268435456,0===e&&(t.fg&=-268435457),t.updateExtended()}_processSGR0(e){e.fg=gl.fg,e.bg=gl.bg,e.extended=e.extended.clone(),e.extended.underlineStyle=0,e.extended.underlineColor&=-67108864,e.updateExtended()}charAttributes(e){if(1===e.length&&0===e.params[0])return this._processSGR0(this._curAttrData),!0;let t,s=e.length,i=this._curAttrData;for(let r=0;r<s;r++)t=e.params[r],t>=30&&t<=37?(i.fg&=-50331904,i.fg|=16777216|t-30):t>=40&&t<=47?(i.bg&=-50331904,i.bg|=16777216|t-40):t>=90&&t<=97?(i.fg&=-50331904,i.fg|=16777224|t-90):t>=100&&t<=107?(i.bg&=-50331904,i.bg|=16777224|t-100):0===t?this._processSGR0(i):1===t?i.fg|=134217728:3===t?i.bg|=67108864:4===t?(i.fg|=268435456,this._processUnderline(e.hasSubParams(r)?e.getSubParams(r)[0]:1,i)):5===t?i.fg|=536870912:7===t?i.fg|=67108864:8===t?i.fg|=1073741824:9===t?i.fg|=2147483648:2===t?i.bg|=134217728:21===t?this._processUnderline(2,i):22===t?(i.fg&=-134217729,i.bg&=-134217729):23===t?i.bg&=-67108865:24===t?(i.fg&=-268435457,this._processUnderline(0,i)):25===t?i.fg&=-536870913:27===t?i.fg&=-67108865:28===t?i.fg&=-1073741825:29===t?i.fg&=2147483647:39===t?(i.fg&=-67108864,i.fg|=16777215&gl.fg):49===t?(i.bg&=-67108864,i.bg|=16777215&gl.bg):38===t||48===t||58===t?r+=this._extractColor(e,r,i):53===t?i.bg|=1073741824:55===t?i.bg&=-1073741825:59===t?(i.extended=i.extended.clone(),i.extended.underlineColor=-1,i.updateExtended()):100===t?(i.fg&=-67108864,i.fg|=16777215&gl.fg,i.bg&=-67108864,i.bg|=16777215&gl.bg):this._logService.debug("Unknown SGR attribute: %d.",t);return!0}deviceStatus(e){switch(e.params[0]){case 5:this._coreService.triggerDataEvent(`${Lo.ESC}[0n`);break;case 6:let e=this._activeBuffer.y+1,t=this._activeBuffer.x+1;this._coreService.triggerDataEvent(`${Lo.ESC}[${e};${t}R`)}return!0}deviceStatusPrivate(e){if(6===e.params[0]){let e=this._activeBuffer.y+1,t=this._activeBuffer.x+1;this._coreService.triggerDataEvent(`${Lo.ESC}[?${e};${t}R`)}return!0}softReset(e){return this._coreService.isCursorHidden=!1,this._onRequestSyncScrollBar.fire(),this._activeBuffer.scrollTop=0,this._activeBuffer.scrollBottom=this._bufferService.rows-1,this._curAttrData=gl.clone(),this._coreService.reset(),this._charsetService.reset(),this._activeBuffer.savedX=0,this._activeBuffer.savedY=this._activeBuffer.ybase,this._activeBuffer.savedCurAttrData.fg=this._curAttrData.fg,this._activeBuffer.savedCurAttrData.bg=this._curAttrData.bg,this._activeBuffer.savedCharset=this._charsetService.charset,this._coreService.decPrivateModes.origin=!1,!0}setCursorStyle(e){let t=0===e.length?1:e.params[0];if(0===t)this._coreService.decPrivateModes.cursorStyle=void 0,this._coreService.decPrivateModes.cursorBlink=void 0;else{switch(t){case 1:case 2:this._coreService.decPrivateModes.cursorStyle="block";break;case 3:case 4:this._coreService.decPrivateModes.cursorStyle="underline";break;case 5:case 6:this._coreService.decPrivateModes.cursorStyle="bar"}let e=t%2==1;this._coreService.decPrivateModes.cursorBlink=e}return!0}setScrollRegion(e){let t,s=e.params[0]||1;return(e.length<2||(t=e.params[1])>this._bufferService.rows||0===t)&&(t=this._bufferService.rows),t>s&&(this._activeBuffer.scrollTop=s-1,this._activeBuffer.scrollBottom=t-1,this._setCursor(0,0)),!0}windowOptions(e){if(!_h(e.params[0],this._optionsService.rawOptions.windowOptions))return!0;let t=e.length>1?e.params[1]:0;switch(e.params[0]){case 14:2!==t&&this._onRequestWindowsOptionsReport.fire(0);break;case 16:this._onRequestWindowsOptionsReport.fire(1);break;case 18:this._bufferService&&this._coreService.triggerDataEvent(`${Lo.ESC}[8;${this._bufferService.rows};${this._bufferService.cols}t`);break;case 22:(0===t||2===t)&&(this._windowTitleStack.push(this._windowTitle),this._windowTitleStack.length>10&&this._windowTitleStack.shift()),(0===t||1===t)&&(this._iconNameStack.push(this._iconName),this._iconNameStack.length>10&&this._iconNameStack.shift());break;case 23:(0===t||2===t)&&this._windowTitleStack.length&&this.setTitle(this._windowTitleStack.pop()),(0===t||1===t)&&this._iconNameStack.length&&this.setIconName(this._iconNameStack.pop())}return!0}saveCursor(e){return this._activeBuffer.savedX=this._activeBuffer.x,this._activeBuffer.savedY=this._activeBuffer.ybase+this._activeBuffer.y,this._activeBuffer.savedCurAttrData.fg=this._curAttrData.fg,this._activeBuffer.savedCurAttrData.bg=this._curAttrData.bg,this._activeBuffer.savedCharset=this._charsetService.charset,!0}restoreCursor(e){return this._activeBuffer.x=this._activeBuffer.savedX||0,this._activeBuffer.y=Math.max(this._activeBuffer.savedY-this._activeBuffer.ybase,0),this._curAttrData.fg=this._activeBuffer.savedCurAttrData.fg,this._curAttrData.bg=this._activeBuffer.savedCurAttrData.bg,this._charsetService.charset=this._savedCharset,this._activeBuffer.savedCharset&&(this._charsetService.charset=this._activeBuffer.savedCharset),this._restrictCursor(),!0}setTitle(e){return this._windowTitle=e,this._onTitleChange.fire(e),!0}setIconName(e){return this._iconName=e,!0}setOrReportIndexedColor(e){let t=[],s=e.split(";");for(;s.length>1;){let e=s.shift(),i=s.shift();if(/^\d+$/.exec(e)){let s=parseInt(e);if(mh(s))if("?"===i)t.push({type:0,index:s});else{let e=hh(i);e&&t.push({type:1,index:s,color:e})}}}return t.length&&this._onColor.fire(t),!0}setHyperlink(e){let t=e.indexOf(";");if(-1===t)return!0;let s=e.slice(0,t).trim(),i=e.slice(t+1);return i?this._createHyperlink(s,i):!s.trim()&&this._finishHyperlink()}_createHyperlink(e,t){this._getCurrentLinkId()&&this._finishHyperlink();let s,i=e.split(":"),r=i.findIndex(e=>e.startsWith("id="));return-1!==r&&(s=i[r].slice(3)||void 0),this._curAttrData.extended=this._curAttrData.extended.clone(),this._curAttrData.extended.urlId=this._oscLinkService.registerLink({id:s,uri:t}),this._curAttrData.updateExtended(),!0}_finishHyperlink(){return this._curAttrData.extended=this._curAttrData.extended.clone(),this._curAttrData.extended.urlId=0,this._curAttrData.updateExtended(),!0}_setOrReportSpecialColor(e,t){let s=e.split(";");for(let e=0;e<s.length&&!(t>=this._specialColors.length);++e,++t)if("?"===s[e])this._onColor.fire([{type:0,index:this._specialColors[t]}]);else{let i=hh(s[e]);i&&this._onColor.fire([{type:1,index:this._specialColors[t],color:i}])}return!0}setOrReportFgColor(e){return this._setOrReportSpecialColor(e,0)}setOrReportBgColor(e){return this._setOrReportSpecialColor(e,1)}setOrReportCursorColor(e){return this._setOrReportSpecialColor(e,2)}restoreIndexedColor(e){if(!e)return this._onColor.fire([{type:2}]),!0;let t=[],s=e.split(";");for(let e=0;e<s.length;++e)if(/^\d+$/.exec(s[e])){let i=parseInt(s[e]);mh(i)&&t.push({type:2,index:i})}return t.length&&this._onColor.fire(t),!0}restoreFgColor(e){return this._onColor.fire([{type:2,index:256}]),!0}restoreBgColor(e){return this._onColor.fire([{type:2,index:257}]),!0}restoreCursorColor(e){return this._onColor.fire([{type:2,index:258}]),!0}nextLine(){return this._activeBuffer.x=0,this.index(),!0}keypadApplicationMode(){return this._logService.debug("Serial port requested application keypad."),this._coreService.decPrivateModes.applicationKeypad=!0,this._onRequestSyncScrollBar.fire(),!0}keypadNumericMode(){return this._logService.debug("Switching back to normal keypad."),this._coreService.decPrivateModes.applicationKeypad=!1,this._onRequestSyncScrollBar.fire(),!0}selectDefaultCharset(){return this._charsetService.setgLevel(0),this._charsetService.setgCharset(0,$l),!0}selectCharset(e){return 2!==e.length?(this.selectDefaultCharset(),!0):("/"===e[0]||this._charsetService.setgCharset(uh[e[0]],xl[e[1]]||$l),!0)}index(){return this._restrictCursor(),this._activeBuffer.y++,this._activeBuffer.y===this._activeBuffer.scrollBottom+1?(this._activeBuffer.y--,this._bufferService.scroll(this._eraseAttrData())):this._activeBuffer.y>=this._bufferService.rows&&(this._activeBuffer.y=this._bufferService.rows-1),this._restrictCursor(),!0}tabSet(){return this._activeBuffer.tabs[this._activeBuffer.x]=!0,!0}reverseIndex(){if(this._restrictCursor(),this._activeBuffer.y===this._activeBuffer.scrollTop){let e=this._activeBuffer.scrollBottom-this._activeBuffer.scrollTop;this._activeBuffer.lines.shiftElements(this._activeBuffer.ybase+this._activeBuffer.y,e,1),this._activeBuffer.lines.set(this._activeBuffer.ybase+this._activeBuffer.y,this._activeBuffer.getBlankLine(this._eraseAttrData())),this._dirtyRowTracker.markRangeDirty(this._activeBuffer.scrollTop,this._activeBuffer.scrollBottom)}else this._activeBuffer.y--,this._restrictCursor();return!0}fullReset(){return this._parser.reset(),this._onRequestReset.fire(),!0}reset(){this._curAttrData=gl.clone(),this._eraseAttrDataInternal=gl.clone()}_eraseAttrData(){return this._eraseAttrDataInternal.bg&=-67108864,this._eraseAttrDataInternal.bg|=67108863&this._curAttrData.bg,this._eraseAttrDataInternal}setgLevel(e){return this._charsetService.setgLevel(e),!0}screenAlignmentPattern(){let e=new qi;e.content=4194373,e.fg=this._curAttrData.fg,e.bg=this._curAttrData.bg,this._setCursor(0,0);for(let t=0;t<this._bufferService.rows;++t){let s=this._activeBuffer.ybase+this._activeBuffer.y+t,i=this._activeBuffer.lines.get(s);i&&(i.fill(e),i.isWrapped=!1)}return this._dirtyRowTracker.markAllDirty(),this._setCursor(0,0),!0}requestStatusString(e,t){let s=this._bufferService.buffer,i=this._optionsService.rawOptions;return(e=>(this._coreService.triggerDataEvent(`${Lo.ESC}${e}${Lo.ESC}\\`),!0))('"q'===e?`P1$r${this._curAttrData.isProtected()?1:0}"q`:'"p'===e?'P1$r61;1"p':"r"===e?`P1$r${s.scrollTop+1};${s.scrollBottom+1}r`:"m"===e?"P1$r0m":" q"===e?`P1$r${{block:2,underline:4,bar:6}[i.cursorStyle]-(i.cursorBlink?1:0)} q`:"P0$r")}markRangeDirty(e,t){this._dirtyRowTracker.markRangeDirty(e,t)}},vh=class{constructor(e){this._bufferService=e,this.clearRange()}clearRange(){this.start=this._bufferService.buffer.y,this.end=this._bufferService.buffer.y}markDirty(e){e<this.start?this.start=e:e>this.end&&(this.end=e)}markRangeDirty(e,t){e>t&&(fh=e,e=t,t=fh),e<this.start&&(this.start=e),t>this.end&&(this.end=t)}markAllDirty(){this.markRangeDirty(0,this._bufferService.rows-1)}};function mh(e){return 0<=e&&e<256}vh=Pi([Ai(0,Zi)],vh);var yh=class extends Dr{constructor(e){super(),this._action=e,this._writeBuffer=[],this._callbacks=[],this._pendingData=0,this._bufferOffset=0,this._isSyncWriting=!1,this._syncCalls=0,this._didUserInput=!1,this._onWriteParsed=this._register(new Xr),this.onWriteParsed=this._onWriteParsed.event}handleUserInput(){this._didUserInput=!0}writeSync(e,t){if(void 0!==t&&this._syncCalls>t)return void(this._syncCalls=0);if(this._pendingData+=e.length,this._writeBuffer.push(e),this._callbacks.push(void 0),this._syncCalls++,this._isSyncWriting)return;let s;for(this._isSyncWriting=!0;s=this._writeBuffer.shift();){this._action(s);let e=this._callbacks.shift();e&&e()}this._pendingData=0,this._bufferOffset=2147483647,this._isSyncWriting=!1,this._syncCalls=0}write(e,t){if(this._pendingData>5e7)throw new Error("write data discarded, use flow control to avoid losing data");if(!this._writeBuffer.length){if(this._bufferOffset=0,this._didUserInput)return this._didUserInput=!1,this._pendingData+=e.length,this._writeBuffer.push(e),this._callbacks.push(t),void this._innerWrite();setTimeout(()=>this._innerWrite())}this._pendingData+=e.length,this._writeBuffer.push(e),this._callbacks.push(t)}_innerWrite(e=0,t=!0){let s=e||performance.now();for(;this._writeBuffer.length>this._bufferOffset;){let e=this._writeBuffer[this._bufferOffset],i=this._action(e,t);if(i){let e=e=>performance.now()-s>=12?setTimeout(()=>this._innerWrite(0,e)):this._innerWrite(s,e);return void i.catch(e=>(queueMicrotask(()=>{throw e}),Promise.resolve(!1))).then(e)}let r=this._callbacks[this._bufferOffset];if(r&&r(),this._bufferOffset++,this._pendingData-=e.length,performance.now()-s>=12)break}this._writeBuffer.length>this._bufferOffset?(this._bufferOffset>50&&(this._writeBuffer=this._writeBuffer.slice(this._bufferOffset),this._callbacks=this._callbacks.slice(this._bufferOffset),this._bufferOffset=0),setTimeout(()=>this._innerWrite())):(this._writeBuffer.length=0,this._callbacks.length=0,this._pendingData=0,this._bufferOffset=0),this._onWriteParsed.fire()}},bh=class{constructor(e){this._bufferService=e,this._nextId=1,this._entriesWithId=new Map,this._dataByLinkId=new Map}registerLink(e){let t=this._bufferService.buffer;if(void 0===e.id){let s=t.addMarker(t.ybase+t.y),i={data:e,id:this._nextId++,lines:[s]};return s.onDispose(()=>this._removeMarkerFromLink(i,s)),this._dataByLinkId.set(i.id,i),i.id}let s=e,i=this._getEntryIdKey(s),r=this._entriesWithId.get(i);if(r)return this.addLineToLink(r.id,t.ybase+t.y),r.id;let n=t.addMarker(t.ybase+t.y),o={id:this._nextId++,key:this._getEntryIdKey(s),data:s,lines:[n]};return n.onDispose(()=>this._removeMarkerFromLink(o,n)),this._entriesWithId.set(o.key,o),this._dataByLinkId.set(o.id,o),o.id}addLineToLink(e,t){let s=this._dataByLinkId.get(e);if(s&&s.lines.every(e=>e.line!==t)){let e=this._bufferService.buffer.addMarker(t);s.lines.push(e),e.onDispose(()=>this._removeMarkerFromLink(s,e))}}getLinkData(e){return this._dataByLinkId.get(e)?.data}_getEntryIdKey(e){return`${e.id};;${e.uri}`}_removeMarkerFromLink(e,t){let s=e.lines.indexOf(t);-1!==s&&(e.lines.splice(s,1),0===e.lines.length&&(void 0!==e.data.id&&this._entriesWithId.delete(e.key),this._dataByLinkId.delete(e.id)))}};bh=Pi([Ai(0,Zi)],bh);var wh=!1,Sh=class extends Dr{constructor(e){super(),this._windowsWrappingHeuristics=this._register(new Lr),this._onBinary=this._register(new Xr),this.onBinary=this._onBinary.event,this._onData=this._register(new Xr),this.onData=this._onData.event,this._onLineFeed=this._register(new Xr),this.onLineFeed=this._onLineFeed.event,this._onResize=this._register(new Xr),this.onResize=this._onResize.event,this._onWriteParsed=this._register(new Xr),this.onWriteParsed=this._onWriteParsed.event,this._onScroll=this._register(new Xr),this._instantiationService=new ul,this.optionsService=this._register(new Tl(e)),this._instantiationService.setService(rr,this.optionsService),this._bufferService=this._register(this._instantiationService.createInstance(Rl)),this._instantiationService.setService(Zi,this._bufferService),this._logService=this._register(this._instantiationService.createInstance(_l)),this._instantiationService.setService(ir,this._logService),this.coreService=this._register(this._instantiationService.createInstance(Bl)),this._instantiationService.setService(er,this.coreService),this.coreMouseService=this._register(this._instantiationService.createInstance(Fl)),this._instantiationService.setService(Qi,this.coreMouseService),this.unicodeService=this._register(this._instantiationService.createInstance(Vl)),this._instantiationService.setService(or,this.unicodeService),this._charsetService=this._instantiationService.createInstance(jl),this._instantiationService.setService(tr,this._charsetService),this._oscLinkService=this._instantiationService.createInstance(bh),this._instantiationService.setService(nr,this._oscLinkService),this._inputHandler=this._register(new gh(this._bufferService,this._charsetService,this.coreService,this._logService,this.optionsService,this._oscLinkService,this.coreMouseService,this.unicodeService)),this._register(Or.forward(this._inputHandler.onLineFeed,this._onLineFeed)),this._register(this._inputHandler),this._register(Or.forward(this._bufferService.onResize,this._onResize)),this._register(Or.forward(this.coreService.onData,this._onData)),this._register(Or.forward(this.coreService.onBinary,this._onBinary)),this._register(this.coreService.onRequestScrollToBottom(()=>this.scrollToBottom(!0))),this._register(this.coreService.onUserInput(()=>this._writeBuffer.handleUserInput())),this._register(this.optionsService.onMultipleOptionChange(["windowsMode","windowsPty"],()=>this._handleWindowsPtyOptionChange())),this._register(this._bufferService.onScroll(()=>{this._onScroll.fire({position:this._bufferService.buffer.ydisp}),this._inputHandler.markRangeDirty(this._bufferService.buffer.scrollTop,this._bufferService.buffer.scrollBottom)})),this._writeBuffer=this._register(new yh((e,t)=>this._inputHandler.parse(e,t))),this._register(Or.forward(this._writeBuffer.onWriteParsed,this._onWriteParsed))}get onScroll(){return this._onScrollApi||(this._onScrollApi=this._register(new Xr),this._onScroll.event(e=>{this._onScrollApi?.fire(e.position)})),this._onScrollApi.event}get cols(){return this._bufferService.cols}get rows(){return this._bufferService.rows}get buffers(){return this._bufferService.buffers}get options(){return this.optionsService.options}set options(e){for(let t in e)this.optionsService.options[t]=e[t]}write(e,t){this._writeBuffer.write(e,t)}writeSync(e,t){this._logService.logLevel<=3&&!wh&&(this._logService.warn("writeSync is unreliable and will be removed soon."),wh=!0),this._writeBuffer.writeSync(e,t)}input(e,t=!0){this.coreService.triggerDataEvent(e,t)}resize(e,t){isNaN(e)||isNaN(t)||(e=Math.max(e,2),t=Math.max(t,1),this._bufferService.resize(e,t))}scroll(e,t=!1){this._bufferService.scroll(e,t)}scrollLines(e,t){this._bufferService.scrollLines(e,t)}scrollPages(e){this.scrollLines(e*(this.rows-1))}scrollToTop(){this.scrollLines(-this._bufferService.buffer.ydisp)}scrollToBottom(e){this.scrollLines(this._bufferService.buffer.ybase-this._bufferService.buffer.ydisp)}scrollToLine(e){let t=e-this._bufferService.buffer.ydisp;0!==t&&this.scrollLines(t)}registerEscHandler(e,t){return this._inputHandler.registerEscHandler(e,t)}registerDcsHandler(e,t){return this._inputHandler.registerDcsHandler(e,t)}registerCsiHandler(e,t){return this._inputHandler.registerCsiHandler(e,t)}registerOscHandler(e,t){return this._inputHandler.registerOscHandler(e,t)}_setup(){this._handleWindowsPtyOptionChange()}reset(){this._inputHandler.reset(),this._bufferService.reset(),this._charsetService.reset(),this.coreService.reset(),this.coreMouseService.reset()}_handleWindowsPtyOptionChange(){let e=!1,t=this.optionsService.rawOptions.windowsPty;t&&void 0!==t.buildNumber&&void 0!==t.buildNumber?e="conpty"===t.backend&&t.buildNumber<21376:this.optionsService.rawOptions.windowsMode&&(e=!0),e?this._enableWindowsWrappingHeuristics():this._windowsWrappingHeuristics.clear()}_enableWindowsWrappingHeuristics(){if(!this._windowsWrappingHeuristics.value){let e=[];e.push(this.onLineFeed(ql.bind(null,this._bufferService))),e.push(this.registerCsiHandler({final:"H"},()=>(ql(this._bufferService),!1))),this._windowsWrappingHeuristics.value=Pr(()=>{for(let t of e)t.dispose()})}}},xh={48:["0",")"],49:["1","!"],50:["2","@"],51:["3","#"],52:["4","$"],53:["5","%"],54:["6","^"],55:["7","&"],56:["8","*"],57:["9","("],186:[";",":"],187:["=","+"],188:[",","<"],189:["-","_"],190:[".",">"],191:["/","?"],192:["`","~"],219:["[","{"],220:["\\","|"],221:["]","}"],222:["'",'"']};var $h=0,kh=class{constructor(e){this._getKey=e,this._array=[],this._insertedValues=[],this._flushInsertedTask=new Na,this._isFlushingInserted=!1,this._deletedIndices=[],this._flushDeletedTask=new Na,this._isFlushingDeleted=!1}clear(){this._array.length=0,this._insertedValues.length=0,this._flushInsertedTask.clear(),this._isFlushingInserted=!1,this._deletedIndices.length=0,this._flushDeletedTask.clear(),this._isFlushingDeleted=!1}insert(e){this._flushCleanupDeleted(),0===this._insertedValues.length&&this._flushInsertedTask.enqueue(()=>this._flushInserted()),this._insertedValues.push(e)}_flushInserted(){let e=this._insertedValues.sort((e,t)=>this._getKey(e)-this._getKey(t)),t=0,s=0,i=new Array(this._array.length+this._insertedValues.length);for(let r=0;r<i.length;r++)s>=this._array.length||this._getKey(e[t])<=this._getKey(this._array[s])?(i[r]=e[t],t++):i[r]=this._array[s++];this._array=i,this._insertedValues.length=0}_flushCleanupInserted(){!this._isFlushingInserted&&this._insertedValues.length>0&&this._flushInsertedTask.flush()}delete(e){if(this._flushCleanupInserted(),0===this._array.length)return!1;let t=this._getKey(e);if(void 0===t||-1===($h=this._search(t))||this._getKey(this._array[$h])!==t)return!1;do{if(this._array[$h]===e)return 0===this._deletedIndices.length&&this._flushDeletedTask.enqueue(()=>this._flushDeleted()),this._deletedIndices.push($h),!0}while(++$h<this._array.length&&this._getKey(this._array[$h])===t);return!1}_flushDeleted(){this._isFlushingDeleted=!0;let e=this._deletedIndices.sort((e,t)=>e-t),t=0,s=new Array(this._array.length-e.length),i=0;for(let r=0;r<this._array.length;r++)e[t]===r?t++:s[i++]=this._array[r];this._array=s,this._deletedIndices.length=0,this._isFlushingDeleted=!1}_flushCleanupDeleted(){!this._isFlushingDeleted&&this._deletedIndices.length>0&&this._flushDeletedTask.flush()}*getKeyIterator(e){if(this._flushCleanupInserted(),this._flushCleanupDeleted(),0!==this._array.length&&(!(($h=this._search(e))<0||$h>=this._array.length)&&this._getKey(this._array[$h])===e))do{yield this._array[$h]}while(++$h<this._array.length&&this._getKey(this._array[$h])===e)}forEachByKey(e,t){if(this._flushCleanupInserted(),this._flushCleanupDeleted(),0!==this._array.length&&(!(($h=this._search(e))<0||$h>=this._array.length)&&this._getKey(this._array[$h])===e))do{t(this._array[$h])}while(++$h<this._array.length&&this._getKey(this._array[$h])===e)}values(){return this._flushCleanupInserted(),this._flushCleanupDeleted(),[...this._array].values()}_search(e){let t=0,s=this._array.length-1;for(;s>=t;){let i=t+s>>1,r=this._getKey(this._array[i]);if(r>e)s=i-1;else{if(!(r<e)){for(;i>0&&this._getKey(this._array[i-1])===e;)i--;return i}t=i+1}}return t}},Ch=0,Eh=0,Rh=class extends Dr{constructor(){super(),this._decorations=new kh(e=>e?.marker.line),this._onDecorationRegistered=this._register(new Xr),this.onDecorationRegistered=this._onDecorationRegistered.event,this._onDecorationRemoved=this._register(new Xr),this.onDecorationRemoved=this._onDecorationRemoved.event,this._register(Pr(()=>this.reset()))}get decorations(){return this._decorations.values()}registerDecoration(e){if(e.marker.isDisposed)return;let t=new Ph(e);if(t){let e=t.marker.onDispose(()=>t.dispose()),s=t.onDispose(()=>{s.dispose(),t&&(this._decorations.delete(t)&&this._onDecorationRemoved.fire(t),e.dispose())});this._decorations.insert(t),this._onDecorationRegistered.fire(t)}return t}reset(){for(let e of this._decorations.values())e.dispose();this._decorations.clear()}*getDecorationsAtCell(e,t,s){let i=0,r=0;for(let n of this._decorations.getKeyIterator(t))i=n.options.x??0,r=i+(n.options.width??1),e>=i&&e<r&&(!s||(n.options.layer??"bottom")===s)&&(yield n)}forEachDecorationAtCell(e,t,s,i){this._decorations.forEachByKey(t,t=>{Ch=t.options.x??0,Eh=Ch+(t.options.width??1),e>=Ch&&e<Eh&&(!s||(t.options.layer??"bottom")===s)&&i(t)})}},Ph=class extends Tr{constructor(e){super(),this.options=e,this.onRenderEmitter=this.add(new Xr),this.onRender=this.onRenderEmitter.event,this._onDispose=this.add(new Xr),this.onDispose=this._onDispose.event,this._cachedBg=null,this._cachedFg=null,this.marker=e.marker,this.options.overviewRulerOptions&&!this.options.overviewRulerOptions.position&&(this.options.overviewRulerOptions.position="full")}get backgroundColorRGB(){return null===this._cachedBg&&(this.options.backgroundColor?this._cachedBg=Ko.toColor(this.options.backgroundColor):this._cachedBg=void 0),this._cachedBg}get foregroundColorRGB(){return null===this._cachedFg&&(this.options.foregroundColor?this._cachedFg=Ko.toColor(this.options.foregroundColor):this._cachedFg=void 0),this._cachedFg}dispose(){this._onDispose.fire(),super.dispose()}},Ah=class{constructor(e,t=1e3){this._renderCallback=e,this._debounceThresholdMS=t,this._lastRefreshMs=0,this._additionalRefreshRequested=!1}dispose(){this._refreshTimeoutID&&clearTimeout(this._refreshTimeoutID)}refresh(e,t,s){this._rowCount=s,e=void 0!==e?e:0,t=void 0!==t?t:this._rowCount-1,this._rowStart=void 0!==this._rowStart?Math.min(this._rowStart,e):e,this._rowEnd=void 0!==this._rowEnd?Math.max(this._rowEnd,t):t;let i=performance.now();if(i-this._lastRefreshMs>=this._debounceThresholdMS)this._lastRefreshMs=i,this._innerRefresh();else if(!this._additionalRefreshRequested){let e=i-this._lastRefreshMs,t=this._debounceThresholdMS-e;this._additionalRefreshRequested=!0,this._refreshTimeoutID=window.setTimeout(()=>{this._lastRefreshMs=performance.now(),this._innerRefresh(),this._additionalRefreshRequested=!1,this._refreshTimeoutID=void 0},t)}}_innerRefresh(){if(void 0===this._rowStart||void 0===this._rowEnd||void 0===this._rowCount)return;let e=Math.max(this._rowStart,0),t=Math.min(this._rowEnd,this._rowCount-1);this._rowStart=void 0,this._rowEnd=void 0,this._renderCallback(e,t)}},Th=class extends Dr{constructor(e,t,s,i){super(),this._terminal=e,this._coreBrowserService=s,this._renderService=i,this._rowColumns=new WeakMap,this._liveRegionLineCount=0,this._charsToConsume=[],this._charsToAnnounce="";let r=this._coreBrowserService.mainDocument;this._accessibilityContainer=r.createElement("div"),this._accessibilityContainer.classList.add("xterm-accessibility"),this._rowContainer=r.createElement("div"),this._rowContainer.setAttribute("role","list"),this._rowContainer.classList.add("xterm-accessibility-tree"),this._rowElements=[];for(let e=0;e<this._terminal.rows;e++)this._rowElements[e]=this._createAccessibilityTreeNode(),this._rowContainer.appendChild(this._rowElements[e]);if(this._topBoundaryFocusListener=e=>this._handleBoundaryFocus(e,0),this._bottomBoundaryFocusListener=e=>this._handleBoundaryFocus(e,1),this._rowElements[0].addEventListener("focus",this._topBoundaryFocusListener),this._rowElements[this._rowElements.length-1].addEventListener("focus",this._bottomBoundaryFocusListener),this._accessibilityContainer.appendChild(this._rowContainer),this._liveRegion=r.createElement("div"),this._liveRegion.classList.add("live-region"),this._liveRegion.setAttribute("aria-live","assertive"),this._accessibilityContainer.appendChild(this._liveRegion),this._liveRegionDebouncer=this._register(new Ah(this._renderRows.bind(this))),!this._terminal.element)throw new Error("Cannot enable accessibility before Terminal.open");this._terminal.element.insertAdjacentElement("afterbegin",this._accessibilityContainer),this._register(this._terminal.onResize(e=>this._handleResize(e.rows))),this._register(this._terminal.onRender(e=>this._refreshRows(e.start,e.end))),this._register(this._terminal.onScroll(()=>this._refreshRows())),this._register(this._terminal.onA11yChar(e=>this._handleChar(e))),this._register(this._terminal.onLineFeed(()=>this._handleChar("\n"))),this._register(this._terminal.onA11yTab(e=>this._handleTab(e))),this._register(this._terminal.onKey(e=>this._handleKey(e.key))),this._register(this._terminal.onBlur(()=>this._clearLiveRegion())),this._register(this._renderService.onDimensionsChange(()=>this._refreshRowsDimensions())),this._register(eo(r,"selectionchange",()=>this._handleSelectionChange())),this._register(this._coreBrowserService.onDprChange(()=>this._refreshRowsDimensions())),this._refreshRowsDimensions(),this._refreshRows(),this._register(Pr(()=>{this._accessibilityContainer.remove(),this._rowElements.length=0}))}_handleTab(e){for(let t=0;t<e;t++)this._handleChar(" ")}_handleChar(e){this._liveRegionLineCount<21&&(this._charsToConsume.length>0?this._charsToConsume.shift()!==e&&(this._charsToAnnounce+=e):this._charsToAnnounce+=e,"\n"===e&&(this._liveRegionLineCount++,21===this._liveRegionLineCount&&(this._liveRegion.textContent+=Bi())))}_clearLiveRegion(){this._liveRegion.textContent="",this._liveRegionLineCount=0}_handleKey(e){this._clearLiveRegion(),/\p{Control}/u.test(e)||this._charsToConsume.push(e)}_refreshRows(e,t){this._liveRegionDebouncer.refresh(e,t,this._terminal.rows)}_renderRows(e,t){let s=this._terminal.buffer,i=s.lines.length.toString();for(let r=e;r<=t;r++){let e=s.lines.get(s.ydisp+r),t=[],n=e?.translateToString(!0,void 0,void 0,t)||"",o=(s.ydisp+r+1).toString(),a=this._rowElements[r];a&&(0===n.length?(a.textContent=" ",this._rowColumns.set(a,[0,1])):(a.textContent=n,this._rowColumns.set(a,t)),a.setAttribute("aria-posinset",o),a.setAttribute("aria-setsize",i),this._alignRowWidth(a))}this._announceCharacters()}_announceCharacters(){0!==this._charsToAnnounce.length&&(this._liveRegion.textContent+=this._charsToAnnounce,this._charsToAnnounce="")}_handleBoundaryFocus(e,t){let s,i,r=e.target,n=this._rowElements[0===t?1:this._rowElements.length-2];if(r.getAttribute("aria-posinset")!==(0===t?"1":`${this._terminal.buffer.lines.length}`)&&e.relatedTarget===n){if(0===t?(s=r,i=this._rowElements.pop(),this._rowContainer.removeChild(i)):(s=this._rowElements.shift(),i=r,this._rowContainer.removeChild(s)),s.removeEventListener("focus",this._topBoundaryFocusListener),i.removeEventListener("focus",this._bottomBoundaryFocusListener),0===t){let e=this._createAccessibilityTreeNode();this._rowElements.unshift(e),this._rowContainer.insertAdjacentElement("afterbegin",e)}else{let e=this._createAccessibilityTreeNode();this._rowElements.push(e),this._rowContainer.appendChild(e)}this._rowElements[0].addEventListener("focus",this._topBoundaryFocusListener),this._rowElements[this._rowElements.length-1].addEventListener("focus",this._bottomBoundaryFocusListener),this._terminal.scrollLines(0===t?-1:1),this._rowElements[0===t?1:this._rowElements.length-2].focus(),e.preventDefault(),e.stopImmediatePropagation()}}_handleSelectionChange(){if(0===this._rowElements.length)return;let e=this._coreBrowserService.mainDocument.getSelection();if(!e)return;if(e.isCollapsed)return void(this._rowContainer.contains(e.anchorNode)&&this._terminal.clearSelection());if(!e.anchorNode||!e.focusNode)return void console.error("anchorNode and/or focusNode are null");let t={node:e.anchorNode,offset:e.anchorOffset},s={node:e.focusNode,offset:e.focusOffset};if((t.node.compareDocumentPosition(s.node)&Node.DOCUMENT_POSITION_PRECEDING||t.node===s.node&&t.offset>s.offset)&&([t,s]=[s,t]),t.node.compareDocumentPosition(this._rowElements[0])&(Node.DOCUMENT_POSITION_CONTAINED_BY|Node.DOCUMENT_POSITION_FOLLOWING)&&(t={node:this._rowElements[0].childNodes[0],offset:0}),!this._rowContainer.contains(t.node))return;let i=this._rowElements.slice(-1)[0];if(s.node.compareDocumentPosition(i)&(Node.DOCUMENT_POSITION_CONTAINED_BY|Node.DOCUMENT_POSITION_PRECEDING)&&(s={node:i,offset:i.textContent?.length??0}),!this._rowContainer.contains(s.node))return;let r=({node:e,offset:t})=>{let s=e instanceof Text?e.parentNode:e,i=parseInt(s?.getAttribute("aria-posinset"),10)-1;if(isNaN(i))return console.warn("row is invalid. Race condition?"),null;let r=this._rowColumns.get(s);if(!r)return console.warn("columns is null. Race condition?"),null;let n=t<r.length?r[t]:r.slice(-1)[0]+1;return n>=this._terminal.cols&&(++i,n=0),{row:i,column:n}},n=r(t),o=r(s);if(n&&o){if(n.row>o.row||n.row===o.row&&n.column>=o.column)throw new Error("invalid range");this._terminal.select(n.column,n.row,(o.row-n.row)*this._terminal.cols-n.column+o.column)}}_handleResize(e){this._rowElements[this._rowElements.length-1].removeEventListener("focus",this._bottomBoundaryFocusListener);for(let e=this._rowContainer.children.length;e<this._terminal.rows;e++)this._rowElements[e]=this._createAccessibilityTreeNode(),this._rowContainer.appendChild(this._rowElements[e]);for(;this._rowElements.length>e;)this._rowContainer.removeChild(this._rowElements.pop());this._rowElements[this._rowElements.length-1].addEventListener("focus",this._bottomBoundaryFocusListener),this._refreshRowsDimensions()}_createAccessibilityTreeNode(){let e=this._coreBrowserService.mainDocument.createElement("div");return e.setAttribute("role","listitem"),e.tabIndex=-1,this._refreshRowDimensions(e),e}_refreshRowsDimensions(){if(this._renderService.dimensions.css.cell.height){Object.assign(this._accessibilityContainer.style,{width:`${this._renderService.dimensions.css.canvas.width}px`,fontSize:`${this._terminal.options.fontSize}px`}),this._rowElements.length!==this._terminal.rows&&this._handleResize(this._terminal.rows);for(let e=0;e<this._terminal.rows;e++)this._refreshRowDimensions(this._rowElements[e]),this._alignRowWidth(this._rowElements[e])}}_refreshRowDimensions(e){e.style.height=`${this._renderService.dimensions.css.cell.height}px`}_alignRowWidth(e){e.style.transform="";let t=e.getBoundingClientRect().width,s=this._rowColumns.get(e)?.slice(-1)?.[0];if(!s)return;let i=s*this._renderService.dimensions.css.cell.width;e.style.transform=`scaleX(${i/t})`}};Th=Pi([Ai(1,sr),Ai(2,dr),Ai(3,pr)],Th);var Dh=class extends Dr{constructor(e,t,s,i,r){super(),this._element=e,this._mouseService=t,this._renderService=s,this._bufferService=i,this._linkProviderService=r,this._linkCacheDisposables=[],this._isMouseOut=!0,this._wasResized=!1,this._activeLine=-1,this._onShowLinkUnderline=this._register(new Xr),this.onShowLinkUnderline=this._onShowLinkUnderline.event,this._onHideLinkUnderline=this._register(new Xr),this.onHideLinkUnderline=this._onHideLinkUnderline.event,this._register(Pr(()=>{Rr(this._linkCacheDisposables),this._linkCacheDisposables.length=0,this._lastMouseEvent=void 0,this._activeProviderReplies?.clear()})),this._register(this._bufferService.onResize(()=>{this._clearCurrentLink(),this._wasResized=!0})),this._register(eo(this._element,"mouseleave",()=>{this._isMouseOut=!0,this._clearCurrentLink()})),this._register(eo(this._element,"mousemove",this._handleMouseMove.bind(this))),this._register(eo(this._element,"mousedown",this._handleMouseDown.bind(this))),this._register(eo(this._element,"mouseup",this._handleMouseUp.bind(this)))}get currentLink(){return this._currentLink}_handleMouseMove(e){this._lastMouseEvent=e;let t=this._positionFromMouseEvent(e,this._element,this._mouseService);if(!t)return;this._isMouseOut=!1;let s=e.composedPath();for(let e=0;e<s.length;e++){let t=s[e];if(t.classList.contains("xterm"))break;if(t.classList.contains("xterm-hover"))return}(!this._lastBufferCell||t.x!==this._lastBufferCell.x||t.y!==this._lastBufferCell.y)&&(this._handleHover(t),this._lastBufferCell=t)}_handleHover(e){if(this._activeLine!==e.y||this._wasResized)return this._clearCurrentLink(),this._askForLink(e,!1),void(this._wasResized=!1);this._currentLink&&this._linkAtPosition(this._currentLink.link,e)||(this._clearCurrentLink(),this._askForLink(e,!0))}_askForLink(e,t){(!this._activeProviderReplies||!t)&&(this._activeProviderReplies?.forEach(e=>{e?.forEach(e=>{e.link.dispose&&e.link.dispose()})}),this._activeProviderReplies=new Map,this._activeLine=e.y);let s=!1;for(let[i,r]of this._linkProviderService.linkProviders.entries())t?this._activeProviderReplies?.get(i)&&(s=this._checkLinkProviderResult(i,e,s)):r.provideLinks(e.y,t=>{if(this._isMouseOut)return;let r=t?.map(e=>({link:e}));this._activeProviderReplies?.set(i,r),s=this._checkLinkProviderResult(i,e,s),this._activeProviderReplies?.size===this._linkProviderService.linkProviders.length&&this._removeIntersectingLinks(e.y,this._activeProviderReplies)})}_removeIntersectingLinks(e,t){let s=new Set;for(let i=0;i<t.size;i++){let r=t.get(i);if(r)for(let t=0;t<r.length;t++){let i=r[t],n=i.link.range.start.y<e?0:i.link.range.start.x,o=i.link.range.end.y>e?this._bufferService.cols:i.link.range.end.x;for(let e=n;e<=o;e++){if(s.has(e)){r.splice(t--,1);break}s.add(e)}}}}_checkLinkProviderResult(e,t,s){if(!this._activeProviderReplies)return s;let i=this._activeProviderReplies.get(e),r=!1;for(let t=0;t<e;t++)(!this._activeProviderReplies.has(t)||this._activeProviderReplies.get(t))&&(r=!0);if(!r&&i){let e=i.find(e=>this._linkAtPosition(e.link,t));e&&(s=!0,this._handleNewLink(e))}if(this._activeProviderReplies.size===this._linkProviderService.linkProviders.length&&!s)for(let e=0;e<this._activeProviderReplies.size;e++){let i=this._activeProviderReplies.get(e)?.find(e=>this._linkAtPosition(e.link,t));if(i){s=!0,this._handleNewLink(i);break}}return s}_handleMouseDown(){this._mouseDownLink=this._currentLink}_handleMouseUp(e){if(!this._currentLink)return;let t=this._positionFromMouseEvent(e,this._element,this._mouseService);t&&this._mouseDownLink&&function(e,t){return e.text===t.text&&e.range.start.x===t.range.start.x&&e.range.start.y===t.range.start.y&&e.range.end.x===t.range.end.x&&e.range.end.y===t.range.end.y}(this._mouseDownLink.link,this._currentLink.link)&&this._linkAtPosition(this._currentLink.link,t)&&this._currentLink.link.activate(e,this._currentLink.link.text)}_clearCurrentLink(e,t){!this._currentLink||!this._lastMouseEvent||(!e||!t||this._currentLink.link.range.start.y>=e&&this._currentLink.link.range.end.y<=t)&&(this._linkLeave(this._element,this._currentLink.link,this._lastMouseEvent),this._currentLink=void 0,Rr(this._linkCacheDisposables),this._linkCacheDisposables.length=0)}_handleNewLink(e){if(!this._lastMouseEvent)return;let t=this._positionFromMouseEvent(this._lastMouseEvent,this._element,this._mouseService);t&&this._linkAtPosition(e.link,t)&&(this._currentLink=e,this._currentLink.state={decorations:{underline:void 0===e.link.decorations||e.link.decorations.underline,pointerCursor:void 0===e.link.decorations||e.link.decorations.pointerCursor},isHovered:!0},this._linkHover(this._element,e.link,this._lastMouseEvent),e.link.decorations={},Object.defineProperties(e.link.decorations,{pointerCursor:{get:()=>this._currentLink?.state?.decorations.pointerCursor,set:e=>{this._currentLink?.state&&this._currentLink.state.decorations.pointerCursor!==e&&(this._currentLink.state.decorations.pointerCursor=e,this._currentLink.state.isHovered&&this._element.classList.toggle("xterm-cursor-pointer",e))}},underline:{get:()=>this._currentLink?.state?.decorations.underline,set:t=>{this._currentLink?.state&&this._currentLink?.state?.decorations.underline!==t&&(this._currentLink.state.decorations.underline=t,this._currentLink.state.isHovered&&this._fireUnderlineEvent(e.link,t))}}}),this._linkCacheDisposables.push(this._renderService.onRenderedViewportChange(e=>{if(!this._currentLink)return;let t=0===e.start?0:e.start+1+this._bufferService.buffer.ydisp,s=this._bufferService.buffer.ydisp+1+e.end;if(this._currentLink.link.range.start.y>=t&&this._currentLink.link.range.end.y<=s&&(this._clearCurrentLink(t,s),this._lastMouseEvent)){let e=this._positionFromMouseEvent(this._lastMouseEvent,this._element,this._mouseService);e&&this._askForLink(e,!1)}})))}_linkHover(e,t,s){this._currentLink?.state&&(this._currentLink.state.isHovered=!0,this._currentLink.state.decorations.underline&&this._fireUnderlineEvent(t,!0),this._currentLink.state.decorations.pointerCursor&&e.classList.add("xterm-cursor-pointer")),t.hover&&t.hover(s,t.text)}_fireUnderlineEvent(e,t){let s=e.range,i=this._bufferService.buffer.ydisp,r=this._createLinkUnderlineEvent(s.start.x-1,s.start.y-i-1,s.end.x,s.end.y-i-1,void 0);(t?this._onShowLinkUnderline:this._onHideLinkUnderline).fire(r)}_linkLeave(e,t,s){this._currentLink?.state&&(this._currentLink.state.isHovered=!1,this._currentLink.state.decorations.underline&&this._fireUnderlineEvent(t,!1),this._currentLink.state.decorations.pointerCursor&&e.classList.remove("xterm-cursor-pointer")),t.leave&&t.leave(s,t.text)}_linkAtPosition(e,t){let s=e.range.start.y*this._bufferService.cols+e.range.start.x,i=e.range.end.y*this._bufferService.cols+e.range.end.x,r=t.y*this._bufferService.cols+t.x;return s<=r&&r<=i}_positionFromMouseEvent(e,t,s){let i=s.getCoords(e,t,this._bufferService.cols,this._bufferService.rows);if(i)return{x:i[0],y:i[1]+this._bufferService.buffer.ydisp}}_createLinkUnderlineEvent(e,t,s,i,r){return{x1:e,y1:t,x2:s,y2:i,cols:this._bufferService.cols,fg:r}}};Dh=Pi([Ai(1,ur),Ai(2,pr),Ai(3,Zi),Ai(4,vr)],Dh);var Lh=class extends Sh{constructor(e={}){super(e),this._linkifier=this._register(new Lr),this.browser=$a,this._keyDownHandled=!1,this._keyDownSeen=!1,this._keyPressHandled=!1,this._unprocessedDeadKey=!1,this._accessibilityManager=this._register(new Lr),this._onCursorMove=this._register(new Xr),this.onCursorMove=this._onCursorMove.event,this._onKey=this._register(new Xr),this.onKey=this._onKey.event,this._onRender=this._register(new Xr),this.onRender=this._onRender.event,this._onSelectionChange=this._register(new Xr),this.onSelectionChange=this._onSelectionChange.event,this._onTitleChange=this._register(new Xr),this.onTitleChange=this._onTitleChange.event,this._onBell=this._register(new Xr),this.onBell=this._onBell.event,this._onFocus=this._register(new Xr),this._onBlur=this._register(new Xr),this._onA11yCharEmitter=this._register(new Xr),this._onA11yTabEmitter=this._register(new Xr),this._onWillOpen=this._register(new Xr),this._setup(),this._decorationService=this._instantiationService.createInstance(Rh),this._instantiationService.setService(ar,this._decorationService),this._linkProviderService=this._instantiationService.createInstance(ba),this._instantiationService.setService(vr,this._linkProviderService),this._linkProviderService.registerLinkProvider(this._instantiationService.createInstance(lr)),this._register(this._inputHandler.onRequestBell(()=>this._onBell.fire())),this._register(this._inputHandler.onRequestRefreshRows(e=>this.refresh(e?.start??0,e?.end??this.rows-1))),this._register(this._inputHandler.onRequestSendFocus(()=>this._reportFocus())),this._register(this._inputHandler.onRequestReset(()=>this.reset())),this._register(this._inputHandler.onRequestWindowsOptionsReport(e=>this._reportWindowsOptions(e))),this._register(this._inputHandler.onColor(e=>this._handleColorEvent(e))),this._register(Or.forward(this._inputHandler.onCursorMove,this._onCursorMove)),this._register(Or.forward(this._inputHandler.onTitleChange,this._onTitleChange)),this._register(Or.forward(this._inputHandler.onA11yChar,this._onA11yCharEmitter)),this._register(Or.forward(this._inputHandler.onA11yTab,this._onA11yTabEmitter)),this._register(this._bufferService.onResize(e=>this._afterResize(e.cols,e.rows))),this._register(Pr(()=>{this._customKeyEventHandler=void 0,this.element?.parentNode?.removeChild(this.element)}))}get linkifier(){return this._linkifier.value}get onFocus(){return this._onFocus.event}get onBlur(){return this._onBlur.event}get onA11yChar(){return this._onA11yCharEmitter.event}get onA11yTab(){return this._onA11yTabEmitter.event}get onWillOpen(){return this._onWillOpen.event}_handleColorEvent(e){if(this._themeService)for(let t of e){let e,s="";switch(t.index){case 256:e="foreground",s="10";break;case 257:e="background",s="11";break;case 258:e="cursor",s="12";break;default:e="ansi",s="4;"+t.index}switch(t.type){case 0:let i=Uo.toColorRGB("ansi"===e?this._themeService.colors.ansi[t.index]:this._themeService.colors[e]);this.coreService.triggerDataEvent(`${Lo.ESC}]${s};${dh(i)}${Bo.ST}`);break;case 1:if("ansi"===e)this._themeService.modifyColors(e=>e.ansi[t.index]=Wo.toColor(...t.color));else{let s=e;this._themeService.modifyColors(e=>e[s]=Wo.toColor(...t.color))}break;case 2:this._themeService.restoreColor(t.index)}}}_setup(){super._setup(),this._customKeyEventHandler=void 0}get buffer(){return this.buffers.active}focus(){this.textarea&&this.textarea.focus({preventScroll:!0})}_handleScreenReaderModeOptionChange(e){e?!this._accessibilityManager.value&&this._renderService&&(this._accessibilityManager.value=this._instantiationService.createInstance(Th,this)):this._accessibilityManager.clear()}_handleTextAreaFocus(e){this.coreService.decPrivateModes.sendFocus&&this.coreService.triggerDataEvent(Lo.ESC+"[I"),this.element.classList.add("focus"),this._showCursor(),this._onFocus.fire()}blur(){return this.textarea?.blur()}_handleTextAreaBlur(){this.textarea.value="",this.refresh(this.buffer.y,this.buffer.y),this.coreService.decPrivateModes.sendFocus&&this.coreService.triggerDataEvent(Lo.ESC+"[O"),this.element.classList.remove("focus"),this._onBlur.fire()}_syncTextArea(){if(!this.textarea||!this.buffer.isCursorInViewport||this._compositionHelper.isComposing||!this._renderService)return;let e=this.buffer.ybase+this.buffer.y,t=this.buffer.lines.get(e);if(!t)return;let s=Math.min(this.buffer.x,this.cols-1),i=this._renderService.dimensions.css.cell.height,r=t.getWidth(s),n=this._renderService.dimensions.css.cell.width*r,o=this.buffer.y*this._renderService.dimensions.css.cell.height,a=s*this._renderService.dimensions.css.cell.width;this.textarea.style.left=a+"px",this.textarea.style.top=o+"px",this.textarea.style.width=n+"px",this.textarea.style.height=i+"px",this.textarea.style.lineHeight=i+"px",this.textarea.style.zIndex="-5"}_initGlobal(){this._bindKeys(),this._register(eo(this.element,"copy",e=>{this.hasSelection()&&function(e,t){e.clipboardData&&e.clipboardData.setData("text/plain",t.selectionText),e.preventDefault()}(e,this._selectionService)}));let e=e=>function(e,t,s,i){e.stopPropagation(),e.clipboardData&&zi(e.clipboardData.getData("text/plain"),t,s,i)}(e,this.textarea,this.coreService,this.optionsService);this._register(eo(this.textarea,"paste",e)),this._register(eo(this.element,"paste",e)),Ra?this._register(eo(this.element,"mousedown",e=>{2===e.button&&Ni(e,this.textarea,this.screenElement,this._selectionService,this.options.rightClickSelectsWord)})):this._register(eo(this.element,"contextmenu",e=>{Ni(e,this.textarea,this.screenElement,this._selectionService,this.options.rightClickSelectsWord)})),Oa&&this._register(eo(this.element,"auxclick",e=>{1===e.button&&Ii(e,this.textarea,this.screenElement)}))}_bindKeys(){this._register(eo(this.textarea,"keyup",e=>this._keyUp(e),!0)),this._register(eo(this.textarea,"keydown",e=>this._keyDown(e),!0)),this._register(eo(this.textarea,"keypress",e=>this._keyPress(e),!0)),this._register(eo(this.textarea,"compositionstart",()=>this._compositionHelper.compositionstart())),this._register(eo(this.textarea,"compositionupdate",e=>this._compositionHelper.compositionupdate(e))),this._register(eo(this.textarea,"compositionend",()=>this._compositionHelper.compositionend())),this._register(eo(this.textarea,"input",e=>this._inputEvent(e),!0)),this._register(this.onRender(()=>this._compositionHelper.updateCompositionElements()))}open(e){if(!e)throw new Error("Terminal requires a parent element.");if(e.isConnected||this._logService.debug("Terminal.open was called on an element that was not attached to the DOM"),this.element?.ownerDocument.defaultView&&this._coreBrowserService)return void(this.element.ownerDocument.defaultView!==this._coreBrowserService.window&&(this._coreBrowserService.window=this.element.ownerDocument.defaultView));this._document=e.ownerDocument,this.options.documentOverride&&this.options.documentOverride instanceof Document&&(this._document=this.optionsService.rawOptions.documentOverride),this.element=this._document.createElement("div"),this.element.dir="ltr",this.element.classList.add("terminal"),this.element.classList.add("xterm"),e.appendChild(this.element);let t=this._document.createDocumentFragment();this._viewportElement=this._document.createElement("div"),this._viewportElement.classList.add("xterm-viewport"),t.appendChild(this._viewportElement),this.screenElement=this._document.createElement("div"),this.screenElement.classList.add("xterm-screen"),this._register(eo(this.screenElement,"mousemove",e=>this.updateCursorStyle(e))),this._helperContainer=this._document.createElement("div"),this._helperContainer.classList.add("xterm-helpers"),this.screenElement.appendChild(this._helperContainer),t.appendChild(this.screenElement);let s=this.textarea=this._document.createElement("textarea");this.textarea.classList.add("xterm-helper-textarea"),this.textarea.setAttribute("aria-label",Di()),za||this.textarea.setAttribute("aria-multiline","false"),this.textarea.setAttribute("autocorrect","off"),this.textarea.setAttribute("autocapitalize","off"),this.textarea.setAttribute("spellcheck","false"),this.textarea.tabIndex=0,this._register(this.optionsService.onSpecificOptionChange("disableStdin",()=>s.readOnly=this.optionsService.rawOptions.disableStdin)),this.textarea.readOnly=this.optionsService.rawOptions.disableStdin,this._coreBrowserService=this._register(this._instantiationService.createInstance(ma,this.textarea,e.ownerDocument.defaultView??window,this._document??typeof window<"u"?window.document:null)),this._instantiationService.setService(dr,this._coreBrowserService),this._register(eo(this.textarea,"focus",e=>this._handleTextAreaFocus(e))),this._register(eo(this.textarea,"blur",()=>this._handleTextAreaBlur())),this._helperContainer.appendChild(this.textarea),this._charSizeService=this._instantiationService.createInstance(_a,this._document,this._helperContainer),this._instantiationService.setService(cr,this._charSizeService),this._themeService=this._instantiationService.createInstance(hl),this._instantiationService.setService(gr,this._themeService),this._characterJoinerService=this._instantiationService.createInstance(ta),this._instantiationService.setService(fr,this._characterJoinerService),this._renderService=this._register(this._instantiationService.createInstance(Ha,this.rows,this.screenElement)),this._instantiationService.setService(pr,this._renderService),this._register(this._renderService.onRenderedViewportChange(e=>this._onRender.fire(e))),this.onResize(e=>this._renderService.resize(e.cols,e.rows)),this._compositionView=this._document.createElement("div"),this._compositionView.classList.add("composition-view"),this._compositionHelper=this._instantiationService.createInstance(Ho,this.textarea,this._compositionView),this._helperContainer.appendChild(this._compositionView),this._mouseService=this._instantiationService.createInstance(Sa),this._instantiationService.setService(ur,this._mouseService);let i=this._linkifier.value=this._register(this._instantiationService.createInstance(Dh,this.screenElement));this.element.appendChild(t);try{this._onWillOpen.fire(this.element)}catch{}this._renderService.hasRenderer()||this._renderService.setRenderer(this._createRenderer()),this._register(this.onCursorMove(()=>{this._renderService.handleCursorMove(),this._syncTextArea()})),this._register(this.onResize(()=>this._renderService.handleResize(this.cols,this.rows))),this._register(this.onBlur(()=>this._renderService.handleBlur())),this._register(this.onFocus(()=>this._renderService.handleFocus())),this._viewport=this._register(this._instantiationService.createInstance(To,this.element,this.screenElement)),this._register(this._viewport.onRequestScrollLines(e=>{super.scrollLines(e,!1),this.refresh(0,this.rows-1)})),this._selectionService=this._register(this._instantiationService.createInstance(Qa,this.element,this.screenElement,i)),this._instantiationService.setService(_r,this._selectionService),this._register(this._selectionService.onRequestScrollLines(e=>this.scrollLines(e.amount,e.suppressScrollEvent))),this._register(this._selectionService.onSelectionChange(()=>this._onSelectionChange.fire())),this._register(this._selectionService.onRequestRedraw(e=>this._renderService.handleSelectionChanged(e.start,e.end,e.columnSelectMode))),this._register(this._selectionService.onLinuxMouseSelection(e=>{this.textarea.value=e,this.textarea.focus(),this.textarea.select()})),this._register(Or.any(this._onScroll.event,this._inputHandler.onScroll)(()=>{this._selectionService.refresh(),this._viewport?.queueSync()})),this._register(this._instantiationService.createInstance(Do,this.screenElement)),this._register(eo(this.element,"mousedown",e=>this._selectionService.handleMouseDown(e))),this.coreMouseService.areMouseEventsActive?(this._selectionService.disable(),this.element.classList.add("enable-mouse-events")):this._selectionService.enable(),this.options.screenReaderMode&&(this._accessibilityManager.value=this._instantiationService.createInstance(Th,this)),this._register(this.optionsService.onSpecificOptionChange("screenReaderMode",e=>this._handleScreenReaderModeOptionChange(e))),this.options.overviewRuler.width&&(this._overviewRulerRenderer=this._register(this._instantiationService.createInstance(Fo,this._viewportElement,this.screenElement))),this.optionsService.onSpecificOptionChange("overviewRuler",e=>{!this._overviewRulerRenderer&&e&&this._viewportElement&&this.screenElement&&(this._overviewRulerRenderer=this._register(this._instantiationService.createInstance(Fo,this._viewportElement,this.screenElement)))}),this._charSizeService.measure(),this.refresh(0,this.rows-1),this._initGlobal(),this.bindMouse()}_createRenderer(){return this._instantiationService.createInstance(pa,this,this._document,this.element,this.screenElement,this._viewportElement,this._helperContainer,this.linkifier)}bindMouse(){let e=this,t=this.element;function s(t){let s,i,r=e._mouseService.getMouseReportCoords(t,e.screenElement);if(!r)return!1;switch(t.overrideType||t.type){case"mousemove":i=32,void 0===t.buttons?(s=3,void 0!==t.button&&(s=t.button<3?t.button:3)):s=1&t.buttons?0:4&t.buttons?1:2&t.buttons?2:3;break;case"mouseup":i=0,s=t.button<3?t.button:3;break;case"mousedown":i=1,s=t.button<3?t.button:3;break;case"wheel":if(e._customWheelEventHandler&&!1===e._customWheelEventHandler(t))return!1;let r=t.deltaY;if(0===r||0===e.coreMouseService.consumeWheelEvent(t,e._renderService?.dimensions?.device?.cell?.height,e._coreBrowserService?.dpr))return!1;i=r<0?0:1,s=4;break;default:return!1}return!(void 0===i||void 0===s||s>4)&&e.coreMouseService.triggerMouseEvent({col:r.col,row:r.row,x:r.x,y:r.y,button:s,action:i,ctrl:t.ctrlKey,alt:t.altKey,shift:t.shiftKey})}let i={mouseup:null,wheel:null,mousedrag:null,mousemove:null},r={mouseup:e=>(s(e),e.buttons||(this._document.removeEventListener("mouseup",i.mouseup),i.mousedrag&&this._document.removeEventListener("mousemove",i.mousedrag)),this.cancel(e)),wheel:e=>(s(e),this.cancel(e,!0)),mousedrag:e=>{e.buttons&&s(e)},mousemove:e=>{e.buttons||s(e)}};this._register(this.coreMouseService.onProtocolChange(e=>{e?("debug"===this.optionsService.rawOptions.logLevel&&this._logService.debug("Binding to mouse events:",this.coreMouseService.explainEvents(e)),this.element.classList.add("enable-mouse-events"),this._selectionService.disable()):(this._logService.debug("Unbinding from mouse events."),this.element.classList.remove("enable-mouse-events"),this._selectionService.enable()),8&e?i.mousemove||(t.addEventListener("mousemove",r.mousemove),i.mousemove=r.mousemove):(t.removeEventListener("mousemove",i.mousemove),i.mousemove=null),16&e?i.wheel||(t.addEventListener("wheel",r.wheel,{passive:!1}),i.wheel=r.wheel):(t.removeEventListener("wheel",i.wheel),i.wheel=null),2&e?i.mouseup||(i.mouseup=r.mouseup):(this._document.removeEventListener("mouseup",i.mouseup),i.mouseup=null),4&e?i.mousedrag||(i.mousedrag=r.mousedrag):(this._document.removeEventListener("mousemove",i.mousedrag),i.mousedrag=null)})),this.coreMouseService.activeProtocol=this.coreMouseService.activeProtocol,this._register(eo(t,"mousedown",e=>{if(e.preventDefault(),this.focus(),this.coreMouseService.areMouseEventsActive&&!this._selectionService.shouldForceSelection(e))return s(e),i.mouseup&&this._document.addEventListener("mouseup",i.mouseup),i.mousedrag&&this._document.addEventListener("mousemove",i.mousedrag),this.cancel(e)})),this._register(eo(t,"wheel",t=>{if(!i.wheel){if(this._customWheelEventHandler&&!1===this._customWheelEventHandler(t))return!1;if(!this.buffer.hasScrollback){if(0===t.deltaY)return!1;if(0===e.coreMouseService.consumeWheelEvent(t,e._renderService?.dimensions?.device?.cell?.height,e._coreBrowserService?.dpr))return this.cancel(t,!0);let s=Lo.ESC+(this.coreService.decPrivateModes.applicationCursorKeys?"O":"[")+(t.deltaY<0?"A":"B");return this.coreService.triggerDataEvent(s,!0),this.cancel(t,!0)}}},{passive:!1}))}refresh(e,t){this._renderService?.refreshRows(e,t)}updateCursorStyle(e){this._selectionService?.shouldColumnSelect(e)?this.element.classList.add("column-select"):this.element.classList.remove("column-select")}_showCursor(){this.coreService.isCursorInitialized||(this.coreService.isCursorInitialized=!0,this.refresh(this.buffer.y,this.buffer.y))}scrollLines(e,t){this._viewport?this._viewport.scrollLines(e):super.scrollLines(e,t),this.refresh(0,this.rows-1)}scrollPages(e){this.scrollLines(e*(this.rows-1))}scrollToTop(){this.scrollLines(-this._bufferService.buffer.ydisp)}scrollToBottom(e){e&&this._viewport?this._viewport.scrollToLine(this.buffer.ybase,!0):this.scrollLines(this._bufferService.buffer.ybase-this._bufferService.buffer.ydisp)}scrollToLine(e){let t=e-this._bufferService.buffer.ydisp;0!==t&&this.scrollLines(t)}paste(e){zi(e,this.textarea,this.coreService,this.optionsService)}attachCustomKeyEventHandler(e){this._customKeyEventHandler=e}attachCustomWheelEventHandler(e){this._customWheelEventHandler=e}registerLinkProvider(e){return this._linkProviderService.registerLinkProvider(e)}registerCharacterJoiner(e){if(!this._characterJoinerService)throw new Error("Terminal must be opened first");let t=this._characterJoinerService.register(e);return this.refresh(0,this.rows-1),t}deregisterCharacterJoiner(e){if(!this._characterJoinerService)throw new Error("Terminal must be opened first");this._characterJoinerService.deregister(e)&&this.refresh(0,this.rows-1)}get markers(){return this.buffer.markers}registerMarker(e){return this.buffer.addMarker(this.buffer.ybase+this.buffer.y+e)}registerDecoration(e){return this._decorationService.registerDecoration(e)}hasSelection(){return!!this._selectionService&&this._selectionService.hasSelection}select(e,t,s){this._selectionService.setSelection(e,t,s)}getSelection(){return this._selectionService?this._selectionService.selectionText:""}getSelectionPosition(){if(this._selectionService&&this._selectionService.hasSelection)return{start:{x:this._selectionService.selectionStart[0],y:this._selectionService.selectionStart[1]},end:{x:this._selectionService.selectionEnd[0],y:this._selectionService.selectionEnd[1]}}}clearSelection(){this._selectionService?.clearSelection()}selectAll(){this._selectionService?.selectAll()}selectLines(e,t){this._selectionService?.selectLines(e,t)}_keyDown(e){if(this._keyDownHandled=!1,this._keyDownSeen=!0,this._customKeyEventHandler&&!1===this._customKeyEventHandler(e))return!1;let t=this.browser.isMac&&this.options.macOptionIsMeta&&e.altKey;if(!t&&!this._compositionHelper.keydown(e))return this.options.scrollOnUserInput&&this.buffer.ybase!==this.buffer.ydisp&&this.scrollToBottom(!0),!1;!t&&("Dead"===e.key||"AltGraph"===e.key)&&(this._unprocessedDeadKey=!0);let s=function(e,t,s,i){let r={type:0,cancel:!1,key:void 0},n=(e.shiftKey?1:0)|(e.altKey?2:0)|(e.ctrlKey?4:0)|(e.metaKey?8:0);switch(e.keyCode){case 0:"UIKeyInputUpArrow"===e.key?r.key=t?Lo.ESC+"OA":Lo.ESC+"[A":"UIKeyInputLeftArrow"===e.key?r.key=t?Lo.ESC+"OD":Lo.ESC+"[D":"UIKeyInputRightArrow"===e.key?r.key=t?Lo.ESC+"OC":Lo.ESC+"[C":"UIKeyInputDownArrow"===e.key&&(r.key=t?Lo.ESC+"OB":Lo.ESC+"[B");break;case 8:r.key=e.ctrlKey?"\b":Lo.DEL,e.altKey&&(r.key=Lo.ESC+r.key);break;case 9:if(e.shiftKey){r.key=Lo.ESC+"[Z";break}r.key=Lo.HT,r.cancel=!0;break;case 13:r.key=e.altKey?Lo.ESC+Lo.CR:Lo.CR,r.cancel=!0;break;case 27:r.key=Lo.ESC,e.altKey&&(r.key=Lo.ESC+Lo.ESC),r.cancel=!0;break;case 37:if(e.metaKey)break;r.key=n?Lo.ESC+"[1;"+(n+1)+"D":t?Lo.ESC+"OD":Lo.ESC+"[D";break;case 39:if(e.metaKey)break;r.key=n?Lo.ESC+"[1;"+(n+1)+"C":t?Lo.ESC+"OC":Lo.ESC+"[C";break;case 38:if(e.metaKey)break;r.key=n?Lo.ESC+"[1;"+(n+1)+"A":t?Lo.ESC+"OA":Lo.ESC+"[A";break;case 40:if(e.metaKey)break;r.key=n?Lo.ESC+"[1;"+(n+1)+"B":t?Lo.ESC+"OB":Lo.ESC+"[B";break;case 45:!e.shiftKey&&!e.ctrlKey&&(r.key=Lo.ESC+"[2~");break;case 46:r.key=n?Lo.ESC+"[3;"+(n+1)+"~":Lo.ESC+"[3~";break;case 36:r.key=n?Lo.ESC+"[1;"+(n+1)+"H":t?Lo.ESC+"OH":Lo.ESC+"[H";break;case 35:r.key=n?Lo.ESC+"[1;"+(n+1)+"F":t?Lo.ESC+"OF":Lo.ESC+"[F";break;case 33:e.shiftKey?r.type=2:e.ctrlKey?r.key=Lo.ESC+"[5;"+(n+1)+"~":r.key=Lo.ESC+"[5~";break;case 34:e.shiftKey?r.type=3:e.ctrlKey?r.key=Lo.ESC+"[6;"+(n+1)+"~":r.key=Lo.ESC+"[6~";break;case 112:r.key=n?Lo.ESC+"[1;"+(n+1)+"P":Lo.ESC+"OP";break;case 113:r.key=n?Lo.ESC+"[1;"+(n+1)+"Q":Lo.ESC+"OQ";break;case 114:r.key=n?Lo.ESC+"[1;"+(n+1)+"R":Lo.ESC+"OR";break;case 115:r.key=n?Lo.ESC+"[1;"+(n+1)+"S":Lo.ESC+"OS";break;case 116:r.key=n?Lo.ESC+"[15;"+(n+1)+"~":Lo.ESC+"[15~";break;case 117:r.key=n?Lo.ESC+"[17;"+(n+1)+"~":Lo.ESC+"[17~";break;case 118:r.key=n?Lo.ESC+"[18;"+(n+1)+"~":Lo.ESC+"[18~";break;case 119:r.key=n?Lo.ESC+"[19;"+(n+1)+"~":Lo.ESC+"[19~";break;case 120:r.key=n?Lo.ESC+"[20;"+(n+1)+"~":Lo.ESC+"[20~";break;case 121:r.key=n?Lo.ESC+"[21;"+(n+1)+"~":Lo.ESC+"[21~";break;case 122:r.key=n?Lo.ESC+"[23;"+(n+1)+"~":Lo.ESC+"[23~";break;case 123:r.key=n?Lo.ESC+"[24;"+(n+1)+"~":Lo.ESC+"[24~";break;default:if(!e.ctrlKey||e.shiftKey||e.altKey||e.metaKey)if(s&&!i||!e.altKey||e.metaKey)!s||e.altKey||e.ctrlKey||e.shiftKey||!e.metaKey?e.key&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&e.keyCode>=48&&1===e.key.length?r.key=e.key:e.key&&e.ctrlKey&&("_"===e.key&&(r.key=Lo.US),"@"===e.key&&(r.key=Lo.NUL)):65===e.keyCode&&(r.type=1);else{let t=xh[e.keyCode]?.[e.shiftKey?1:0];if(t)r.key=Lo.ESC+t;else if(e.keyCode>=65&&e.keyCode<=90){let t=e.ctrlKey?e.keyCode-64:e.keyCode+32,s=String.fromCharCode(t);e.shiftKey&&(s=s.toUpperCase()),r.key=Lo.ESC+s}else if(32===e.keyCode)r.key=Lo.ESC+(e.ctrlKey?Lo.NUL:" ");else if("Dead"===e.key&&e.code.startsWith("Key")){let t=e.code.slice(3,4);e.shiftKey||(t=t.toLowerCase()),r.key=Lo.ESC+t,r.cancel=!0}}else e.keyCode>=65&&e.keyCode<=90?r.key=String.fromCharCode(e.keyCode-64):32===e.keyCode?r.key=Lo.NUL:e.keyCode>=51&&e.keyCode<=55?r.key=String.fromCharCode(e.keyCode-51+27):56===e.keyCode?r.key=Lo.DEL:219===e.keyCode?r.key=Lo.ESC:220===e.keyCode?r.key=Lo.FS:221===e.keyCode&&(r.key=Lo.GS)}return r}(e,this.coreService.decPrivateModes.applicationCursorKeys,this.browser.isMac,this.options.macOptionIsMeta);if(this.updateCursorStyle(e),3===s.type||2===s.type){let t=this.rows-1;return this.scrollLines(2===s.type?-t:t),this.cancel(e,!0)}return 1===s.type&&this.selectAll(),!!(this._isThirdLevelShift(this.browser,e)||(s.cancel&&this.cancel(e,!0),!s.key)||e.key&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&1===e.key.length&&e.key.charCodeAt(0)>=65&&e.key.charCodeAt(0)<=90)||(this._unprocessedDeadKey?(this._unprocessedDeadKey=!1,!0):((s.key===Lo.ETX||s.key===Lo.CR)&&(this.textarea.value=""),this._onKey.fire({key:s.key,domEvent:e}),this._showCursor(),this.coreService.triggerDataEvent(s.key,!0),!this.optionsService.rawOptions.screenReaderMode||e.altKey||e.ctrlKey?this.cancel(e,!0):void(this._keyDownHandled=!0)))}_isThirdLevelShift(e,t){let s=e.isMac&&!this.options.macOptionIsMeta&&t.altKey&&!t.ctrlKey&&!t.metaKey||e.isWindows&&t.altKey&&t.ctrlKey&&!t.metaKey||e.isWindows&&t.getModifierState("AltGraph");return"keypress"===t.type?s:s&&(!t.keyCode||t.keyCode>47)}_keyUp(e){this._keyDownSeen=!1,(!this._customKeyEventHandler||!1!==this._customKeyEventHandler(e))&&(function(e){return 16===e.keyCode||17===e.keyCode||18===e.keyCode}(e)||this.focus(),this.updateCursorStyle(e),this._keyPressHandled=!1)}_keyPress(e){let t;if(this._keyPressHandled=!1,this._keyDownHandled||this._customKeyEventHandler&&!1===this._customKeyEventHandler(e))return!1;if(this.cancel(e),e.charCode)t=e.charCode;else if(null===e.which||void 0===e.which)t=e.keyCode;else{if(0===e.which||0===e.charCode)return!1;t=e.which}return!(!t||(e.altKey||e.ctrlKey||e.metaKey)&&!this._isThirdLevelShift(this.browser,e))&&(t=String.fromCharCode(t),this._onKey.fire({key:t,domEvent:e}),this._showCursor(),this.coreService.triggerDataEvent(t,!0),this._keyPressHandled=!0,this._unprocessedDeadKey=!1,!0)}_inputEvent(e){if(e.data&&"insertText"===e.inputType&&(!e.composed||!this._keyDownSeen)&&!this.optionsService.rawOptions.screenReaderMode){if(this._keyPressHandled)return!1;this._unprocessedDeadKey=!1;let t=e.data;return this.coreService.triggerDataEvent(t,!0),this.cancel(e),!0}return!1}resize(e,t){e!==this.cols||t!==this.rows?super.resize(e,t):this._charSizeService&&!this._charSizeService.hasValidSize&&this._charSizeService.measure()}_afterResize(e,t){this._charSizeService?.measure()}clear(){if(0!==this.buffer.ybase||0!==this.buffer.y){this.buffer.clearAllMarkers(),this.buffer.lines.set(0,this.buffer.lines.get(this.buffer.ybase+this.buffer.y)),this.buffer.lines.length=1,this.buffer.ydisp=0,this.buffer.ybase=0,this.buffer.y=0;for(let e=1;e<this.rows;e++)this.buffer.lines.push(this.buffer.getBlankLine(gl));this._onScroll.fire({position:this.buffer.ydisp}),this.refresh(0,this.rows-1)}}reset(){this.options.rows=this.rows,this.options.cols=this.cols;let e=this._customKeyEventHandler;this._setup(),super.reset(),this._selectionService?.reset(),this._decorationService.reset(),this._customKeyEventHandler=e,this.refresh(0,this.rows-1)}clearTextureAtlas(){this._renderService?.clearTextureAtlas()}_reportFocus(){this.element?.classList.contains("focus")?this.coreService.triggerDataEvent(Lo.ESC+"[I"):this.coreService.triggerDataEvent(Lo.ESC+"[O")}_reportWindowsOptions(e){if(this._renderService)switch(e){case 0:let e=this._renderService.dimensions.css.canvas.width.toFixed(0),t=this._renderService.dimensions.css.canvas.height.toFixed(0);this.coreService.triggerDataEvent(`${Lo.ESC}[4;${t};${e}t`);break;case 1:let s=this._renderService.dimensions.css.cell.width.toFixed(0),i=this._renderService.dimensions.css.cell.height.toFixed(0);this.coreService.triggerDataEvent(`${Lo.ESC}[6;${i};${s}t`)}}cancel(e,t){if(this.options.cancelEvents||t)return e.preventDefault(),e.stopPropagation(),!1}};var Mh=class{constructor(){this._addons=[]}dispose(){for(let e=this._addons.length-1;e>=0;e--)this._addons[e].instance.dispose()}loadAddon(e,t){let s={instance:t,dispose:t.dispose,isDisposed:!1};this._addons.push(s),t.dispose=()=>this._wrappedAddonDispose(s),t.activate(e)}_wrappedAddonDispose(e){if(e.isDisposed)return;let t=-1;for(let s=0;s<this._addons.length;s++)if(this._addons[s]===e){t=s;break}if(-1===t)throw new Error("Could not dispose an addon that has not been loaded");e.isDisposed=!0,e.dispose.apply(e.instance),this._addons.splice(t,1)}},Bh=class{constructor(e){this._line=e}get isWrapped(){return this._line.isWrapped}get length(){return this._line.length}getCell(e,t){if(!(e<0||e>=this._line.length))return t?(this._line.loadCell(e,t),t):this._line.loadCell(e,new qi)}translateToString(e,t,s){return this._line.translateToString(e,t,s)}},Oh=class{constructor(e,t){this._buffer=e,this.type=t}init(e){return this._buffer=e,this}get cursorY(){return this._buffer.y}get cursorX(){return this._buffer.x}get viewportY(){return this._buffer.ydisp}get baseY(){return this._buffer.ybase}get length(){return this._buffer.lines.length}getLine(e){let t=this._buffer.lines.get(e);if(t)return new Bh(t)}getNullCell(){return new qi}},zh=class extends Dr{constructor(e){super(),this._core=e,this._onBufferChange=this._register(new Xr),this.onBufferChange=this._onBufferChange.event,this._normal=new Oh(this._core.buffers.normal,"normal"),this._alternate=new Oh(this._core.buffers.alt,"alternate"),this._core.buffers.onBufferActivate(()=>this._onBufferChange.fire(this.active))}get active(){if(this._core.buffers.active===this._core.buffers.normal)return this.normal;if(this._core.buffers.active===this._core.buffers.alt)return this.alternate;throw new Error("Active buffer is neither normal nor alternate")}get normal(){return this._normal.init(this._core.buffers.normal)}get alternate(){return this._alternate.init(this._core.buffers.alt)}},Ih=class{constructor(e){this._core=e}registerCsiHandler(e,t){return this._core.registerCsiHandler(e,e=>t(e.toArray()))}addCsiHandler(e,t){return this.registerCsiHandler(e,t)}registerDcsHandler(e,t){return this._core.registerDcsHandler(e,(e,s)=>t(e,s.toArray()))}addDcsHandler(e,t){return this.registerDcsHandler(e,t)}registerEscHandler(e,t){return this._core.registerEscHandler(e,t)}addEscHandler(e,t){return this.registerEscHandler(e,t)}registerOscHandler(e,t){return this._core.registerOscHandler(e,t)}addOscHandler(e,t){return this.registerOscHandler(e,t)}},Nh=class{constructor(e){this._core=e}register(e){this._core.unicodeService.register(e)}get versions(){return this._core.unicodeService.versions}get activeVersion(){return this._core.unicodeService.activeVersion}set activeVersion(e){this._core.unicodeService.activeVersion=e}},Fh=["cols","rows"],Hh=0,Wh=class extends Dr{constructor(e){super(),this._core=this._register(new Lh(e)),this._addonManager=this._register(new Mh),this._publicOptions={...this._core.options};let t=e=>this._core.options[e],s=(e,t)=>{this._checkReadonlyOptions(e),this._core.options[e]=t};for(let e in this._core.options){let i={get:t.bind(this,e),set:s.bind(this,e)};Object.defineProperty(this._publicOptions,e,i)}}_checkReadonlyOptions(e){if(Fh.includes(e))throw new Error(`Option "${e}" can only be set in the constructor`)}_checkProposedApi(){if(!this._core.optionsService.rawOptions.allowProposedApi)throw new Error("You must set the allowProposedApi option to true to use proposed API")}get onBell(){return this._core.onBell}get onBinary(){return this._core.onBinary}get onCursorMove(){return this._core.onCursorMove}get onData(){return this._core.onData}get onKey(){return this._core.onKey}get onLineFeed(){return this._core.onLineFeed}get onRender(){return this._core.onRender}get onResize(){return this._core.onResize}get onScroll(){return this._core.onScroll}get onSelectionChange(){return this._core.onSelectionChange}get onTitleChange(){return this._core.onTitleChange}get onWriteParsed(){return this._core.onWriteParsed}get element(){return this._core.element}get parser(){return this._parser||(this._parser=new Ih(this._core)),this._parser}get unicode(){return this._checkProposedApi(),new Nh(this._core)}get textarea(){return this._core.textarea}get rows(){return this._core.rows}get cols(){return this._core.cols}get buffer(){return this._buffer||(this._buffer=this._register(new zh(this._core))),this._buffer}get markers(){return this._checkProposedApi(),this._core.markers}get modes(){let e=this._core.coreService.decPrivateModes,t="none";switch(this._core.coreMouseService.activeProtocol){case"X10":t="x10";break;case"VT200":t="vt200";break;case"DRAG":t="drag";break;case"ANY":t="any"}return{applicationCursorKeysMode:e.applicationCursorKeys,applicationKeypadMode:e.applicationKeypad,bracketedPasteMode:e.bracketedPasteMode,insertMode:this._core.coreService.modes.insertMode,mouseTrackingMode:t,originMode:e.origin,reverseWraparoundMode:e.reverseWraparound,sendFocusMode:e.sendFocus,synchronizedOutputMode:e.synchronizedOutput,wraparoundMode:e.wraparound}}get options(){return this._publicOptions}set options(e){for(let t in e)this._publicOptions[t]=e[t]}blur(){this._core.blur()}focus(){this._core.focus()}input(e,t=!0){this._core.input(e,t)}resize(e,t){this._verifyIntegers(e,t),this._core.resize(e,t)}open(e){this._core.open(e)}attachCustomKeyEventHandler(e){this._core.attachCustomKeyEventHandler(e)}attachCustomWheelEventHandler(e){this._core.attachCustomWheelEventHandler(e)}registerLinkProvider(e){return this._core.registerLinkProvider(e)}registerCharacterJoiner(e){return this._checkProposedApi(),this._core.registerCharacterJoiner(e)}deregisterCharacterJoiner(e){this._checkProposedApi(),this._core.deregisterCharacterJoiner(e)}registerMarker(e=0){return this._verifyIntegers(e),this._core.registerMarker(e)}registerDecoration(e){return this._checkProposedApi(),this._verifyPositiveIntegers(e.x??0,e.width??0,e.height??0),this._core.registerDecoration(e)}hasSelection(){return this._core.hasSelection()}select(e,t,s){this._verifyIntegers(e,t,s),this._core.select(e,t,s)}getSelection(){return this._core.getSelection()}getSelectionPosition(){return this._core.getSelectionPosition()}clearSelection(){this._core.clearSelection()}selectAll(){this._core.selectAll()}selectLines(e,t){this._verifyIntegers(e,t),this._core.selectLines(e,t)}dispose(){super.dispose()}scrollLines(e){this._verifyIntegers(e),this._core.scrollLines(e)}scrollPages(e){this._verifyIntegers(e),this._core.scrollPages(e)}scrollToTop(){this._core.scrollToTop()}scrollToBottom(){this._core.scrollToBottom()}scrollToLine(e){this._verifyIntegers(e),this._core.scrollToLine(e)}clear(){this._core.clear()}write(e,t){this._core.write(e,t)}writeln(e,t){this._core.write(e),this._core.write("\r\n",t)}paste(e){this._core.paste(e)}refresh(e,t){this._verifyIntegers(e,t),this._core.refresh(e,t)}reset(){this._core.reset()}clearTextureAtlas(){this._core.clearTextureAtlas()}loadAddon(e){this._addonManager.loadAddon(this,e)}static get strings(){return{get promptLabel(){return Di()},set promptLabel(e){Li(e)},get tooMuchOutput(){return Bi()},set tooMuchOutput(e){Oi(e)}}}_verifyIntegers(...e){for(Hh of e)if(Hh===1/0||isNaN(Hh)||Hh%1!=0)throw new Error("This API only accepts integers")}_verifyPositiveIntegers(...e){for(Hh of e)if(Hh&&(Hh===1/0||isNaN(Hh)||Hh%1!=0||Hh<0))throw new Error("This API only accepts positive integers")}},Uh=class{activate(e){this._terminal=e}dispose(){}fit(){let e=this.proposeDimensions();if(!e||!this._terminal||isNaN(e.cols)||isNaN(e.rows))return;let t=this._terminal._core;(this._terminal.rows!==e.rows||this._terminal.cols!==e.cols)&&(t._renderService.clear(),this._terminal.resize(e.cols,e.rows))}proposeDimensions(){if(!this._terminal||!this._terminal.element||!this._terminal.element.parentElement)return;let e=this._terminal._core._renderService.dimensions;if(0===e.css.cell.width||0===e.css.cell.height)return;let t=0===this._terminal.options.scrollback?0:this._terminal.options.overviewRuler?.width||14,s=window.getComputedStyle(this._terminal.element.parentElement),i=parseInt(s.getPropertyValue("height")),r=Math.max(0,parseInt(s.getPropertyValue("width"))),n=window.getComputedStyle(this._terminal.element),o=i-(parseInt(n.getPropertyValue("padding-top"))+parseInt(n.getPropertyValue("padding-bottom"))),a=r-(parseInt(n.getPropertyValue("padding-right"))+parseInt(n.getPropertyValue("padding-left")))-t;return{cols:Math.max(2,Math.floor(a/e.css.cell.width)),rows:Math.max(1,Math.floor(o/e.css.cell.height))}}};const Kh=[30,60,120],Vh=new TextEncoder;new TextDecoder;const jh={user_closed:"You closed the session.",remote_closed:"The shell exited.",connection_lost:"The connection to Home Assistant was lost.",max_duration:"The session reached its maximum duration.",unloaded:"HA SOC was reloaded.",error:"The session ended with an error."},qh={background:"#1c2128",foreground:"#e6edf3",cursor:"#58a6ff",selectionBackground:"#264f78",black:"#484f58",red:"#ff7b72",green:"#3fb950",yellow:"#d29922",blue:"#58a6ff",magenta:"#bc8cff",cyan:"#39c5cf",white:"#b1bac4",brightBlack:"#6e7681",brightRed:"#ffa198",brightGreen:"#56d364",brightYellow:"#e3b341",brightBlue:"#79c0ff",brightMagenta:"#d2a8ff",brightCyan:"#56d4dd",brightWhite:"#f0f6fc"},Yh=[{id:"theme",label:"Theme code font",stack:""},{id:"cascadia",label:"Cascadia Mono",stack:"'Cascadia Mono', 'Cascadia Code'"},{id:"consolas",label:"Consolas",stack:"Consolas"},{id:"jetbrains",label:"JetBrains Mono",stack:"'JetBrains Mono'"},{id:"fira",label:"Fira Code",stack:"'Fira Code', 'Fira Mono'"},{id:"menlo",label:"Menlo / SF Mono",stack:"Menlo, 'SF Mono'"},{id:"roboto",label:"Roboto Mono",stack:"'Roboto Mono'"},{id:"dejavu",label:"DejaVu Sans Mono",stack:"'DejaVu Sans Mono'"},{id:"courier",label:"Courier New",stack:"'Courier New'"},{id:"mono",label:"Browser monospace",stack:"monospace"}],Gh="Consolas, 'DejaVu Sans Mono', 'Courier New', monospace",Xh=[11,12,13,14,15,16,18,20],Jh=[1,1.1,1.2,1.3,1.4],Zh="ha_soc.terminal.font",Qh={family:"theme",size:14,lineHeight:1.2},ec=new Map;let tc=class extends ae{constructor(){super(...arguments),this._status=null,this._error=null,this._open=null,this._ended=null,this._prefs=(()=>{try{const e=window.localStorage.getItem(Zh);if(!e)return{...Qh};const t=JSON.parse(e);return{family:Yh.some(e=>e.id===t.family)?t.family:Qh.family,size:Xh.includes(t.size)?t.size:Qh.size,lineHeight:Jh.includes(t.lineHeight)?t.lineHeight:Qh.lineHeight}}catch{return{...Qh}}})(),this._busy=!1,this._isOwner=!1,this._feedback=null,this._appBusy=!1,this._runCommand="",this._runTimeout=30,this._runBusy=!1,this._runOutput=null,this._runError=null,this._runHistory=[],this._stripAnsi=!0,this._sessionBusy=null,this._term=null,this._fit=null,this._unsubscribe=null,this._resizeObserver=null,this._lastOutputStartRow=null,this._lastOutputEndRow=null,this._pendingOutputStartRow=null}connectedCallback(){super.connectedCallback(),this._refresh(),Me(this.hass).then(e=>{this._isOwner=!!e.is_owner}).catch(()=>{})}disconnectedCallback(){this._close("user_closed"),super.disconnectedCallback()}updated(e){e.has("hass")&&this._term&&(this._term.options.theme=this._theme())}async _refresh(){try{this._status=await(e=this.hass,we(e,{type:"ha_soc/terminal/status"})),this._error=null}catch(e){this._error=e.message||String(e)}var e}_theme(){const e=getComputedStyle(this),t=(t,s)=>e.getPropertyValue(t).trim()||s,s=this.hass?.themes?.darkMode??!0,i=t("--code-editor-background-color",s?qh.background:"#f6f8fa"),r=t("--primary-text-color",s?qh.foreground:"#1f2328"),n=t("--primary-color",qh.blue),o={...qh,background:i,foreground:r,cursor:n,cursorAccent:i,selectionBackground:t("--accent-color",n)+"55",blue:n,brightBlue:n,red:t("--error-color",qh.red),brightRed:t("--error-color",qh.brightRed),green:t("--success-color",qh.green),brightGreen:t("--success-color",qh.brightGreen),yellow:t("--warning-color",qh.yellow),brightYellow:t("--warning-color",qh.brightYellow),cyan:t("--info-color",qh.cyan),brightCyan:t("--info-color",qh.brightCyan)};return s||(o.black="#24292f",o.white="#6e7781",o.brightBlack="#57606a",o.brightWhite="#1f2328"),this.style.setProperty("--soc-term-bg",i),o}async _start(){if(!this._busy&&!this._open){this._busy=!0,this._error=null,this._ended=null;try{await this.updateComplete;const n=new Wh({cursorBlink:!0,fontSize:this._prefs.size,fontFamily:this._fontFamily(),lineHeight:this._prefs.lineHeight,scrollback:5e3,allowProposedApi:!1,theme:this._theme()}),o=new Uh;n.loadAddon(o),n.open(this._box),o.fit(),this._term=n,this._fit=o,this._lastOutputStartRow=null,this._lastOutputEndRow=null,this._pendingOutputStartRow=null,n.parser.registerOscHandler(133,e=>{const t=e.split(";")[0],s=n.buffer.active.baseY+n.buffer.active.cursorY;return"C"===t?this._pendingOutputStartRow=s:"A"===t&&null!==this._pendingOutputStartRow&&(this._lastOutputStartRow=this._pendingOutputStartRow,this._lastOutputEndRow=s,this._pendingOutputStartRow=null),!1});const a=await(e=this.hass,t="self",s=n.cols,i=n.rows,r=e=>this._onEvent(e),new Promise((n,o)=>{let a=null,l=!1;const h=window.setTimeout(()=>{l||(l=!0,a?.(),o(new Error("The Terminal app did not answer in time.")))},15e3);e.connection.subscribeMessage(e=>{if("opened"===e.kind){if(l)return;l=!0,window.clearTimeout(h);const{kind:t,...s}=e;return void n({result:s,unsubscribe:a??(async()=>{})})}r(e)},{type:"ha_soc/terminal/open",target:t,cols:s,rows:i}).then(e=>{a=e}).catch(e=>{l||(l=!0,window.clearTimeout(h),o(e))})}));this._open=a.result,this._unsubscribe=a.unsubscribe,n.onData(e=>{this._open&&((e,t,s)=>we(e,{type:"ha_soc/terminal/input",session_id:t,data:s}))(this.hass,this._open.session_id,(e=>{const t=Vh.encode(e);let s="";for(const e of t)s+=String.fromCharCode(e);return btoa(s)})(e)).catch(e=>{this._error=e.message||String(e)})}),n.onResize(({cols:e,rows:t})=>{this._open&&((e,t,s,i)=>we(e,{type:"ha_soc/terminal/resize",session_id:t,cols:s,rows:i}))(this.hass,this._open.session_id,e,t).catch(()=>{})}),this._resizeObserver=new ResizeObserver(()=>{window.clearTimeout(this._resizeTimer),this._resizeTimer=window.setTimeout(()=>this._fit?.fit(),80)}),this._resizeObserver.observe(this._box),n.focus()}catch(e){this._error=e.message||String(e),this._teardownTerminal()}finally{this._busy=!1}var e,t,s,i,r}}_fontFamily(){const e=Yh.find(e=>e.id===this._prefs.family)??Yh[0];if("theme"===e.id){const e=getComputedStyle(this).getPropertyValue("--ha-font-family-code").trim();return e&&"monospace"!==e?`${e}, ${Gh}`:Gh}return"mono"===e.id?"monospace":`${e.stack}, ${Gh}`}_setPrefs(e){this._prefs={...this._prefs,...e},(e=>{try{window.localStorage.setItem(Zh,JSON.stringify(e))}catch{}})(this._prefs);const t=this._term;t&&(t.options.fontFamily=this._fontFamily(),t.options.fontSize=this._prefs.size,t.options.lineHeight=this._prefs.lineHeight,this._fit?.fit(),t.focus())}_renderFontControls(){const e=this._prefs;return K`
      <label class="font-ctl">
        Font
        <select
          @change=${e=>this._setPrefs({family:e.target.value})}
        >
          ${Yh.map(t=>{const s="theme"===t.id||"mono"===t.id||(e=>{const t=ec.get(e);if(void 0!==t)return t;let s=!1;try{const t=document.createElement("canvas").getContext("2d");if(t){const i="mmmmmmmmmmlli1|WWW0O",r=e=>(t.font=`32px ${e}`,t.measureText(i).width);for(const t of["monospace","serif","sans-serif"])if(r(`${e}, ${t}`)!==r(t)){s=!0;break}}}catch{s=!1}return ec.set(e,s),s})(t.stack.split(",")[0].trim());return K`<option value=${t.id} ?selected=${t.id===e.family} ?disabled=${!s}>
              ${t.label}${s?"":" (not installed)"}
            </option>`})}
        </select>
      </label>
      <label class="font-ctl">
        Size
        <select
          @change=${e=>this._setPrefs({size:Number(e.target.value)})}
        >
          ${Xh.map(t=>K`<option value=${t} ?selected=${t===e.size}>${t}px</option>`)}
        </select>
      </label>
      <label class="font-ctl">
        Line
        <select
          @change=${e=>this._setPrefs({lineHeight:Number(e.target.value)})}
        >
          ${Jh.map(t=>K`<option value=${t} ?selected=${t===e.lineHeight}>${t.toFixed(1)}</option>`)}
        </select>
      </label>
    `}_onEvent(e){"output"===e.kind&&this._term?this._term.write((e=>{const t=atob(e),s=new Uint8Array(t.length);for(let e=0;e<t.length;e++)s[e]=t.charCodeAt(e);return s})(e.data)):"closed"===e.kind&&(this._ended={reason:e.reason,duration:e.duration_seconds},this._open=null,this._teardownSubscription(),this._refresh())}async _close(e){const t=this._open;if(this._open=null,t){try{await Ve(this.hass,t.session_id)}catch{}this._ended||(this._ended={reason:e,duration:0})}await this._teardownSubscription(),this._teardownTerminal(),this._refresh()}async _teardownSubscription(){const e=this._unsubscribe;if(this._unsubscribe=null,e)try{await e()}catch{}}_teardownTerminal(){this._resizeObserver?.disconnect(),this._resizeObserver=null,this._term?.dispose(),this._term=null,this._fit=null}_showFeedback(e){window.clearTimeout(this._feedbackTimer),this._feedback=e,this._feedbackTimer=window.setTimeout(()=>{this._feedback=null},3e3)}_rowsText(e,t){const s=this._term;if(!s)return"";const i=s.buffer.active,r=[];for(let s=e;s<t;s++){const e=i.getLine(s);e&&r.push(e.translateToString(!0).replace(/\s+$/u,""))}return r.join("\n")}_screenText(){const e=this._term;if(!e)return"";const t=e.buffer.active.baseY;return this._rowsText(t,t+e.rows)}_allText(){const e=this._term;return e?this._rowsText(0,e.buffer.active.baseY+e.rows):""}_lastOutputText(){return null===this._lastOutputStartRow||null===this._lastOutputEndRow?"":this._rowsText(this._lastOutputStartRow,this._lastOutputEndRow)}async _export(e,t,s,i){if(!t)return void this._showFeedback("Nothing to "+s);const r=qt(t),n=jt(t);try{"copy"===s?await Yt(t):Gt(t,`${i??"ha-soc-terminal"}-${Xt()}.txt`)}catch(e){return void(this._error=e.message||String(e))}this._showFeedback(`${"copy"===s?"Copied":"Downloaded"} ${r} line(s)`);try{const s=await Vt(t);await je(this.hass,e,r,n,s,this._open?.session_id)}catch{this._showFeedback(`${"copy"===s?"Copied":"Downloaded"} ${r} line(s) (audit record failed)`)}}async _downloadTranscript(e){try{const t=await((e,t)=>we(e,{type:"ha_soc/terminal/transcript",session_id:t}))(this.hass,e),s=this._stripAnsi?(e=>e.replace(/\x1b\][^\x07]*(\x07|\x1b\\)/g,"").replace(/\x1b\[[0-9;?]*[a-zA-Z]/g,"").replace(/\x1b[()][A-Za-z0-9]/g,""))(t.text):t.text;Gt(s,`ha-soc-terminal-transcript-${e}.txt`),this._showFeedback(`Downloaded transcript for ${e}`)}catch(e){this._error=e.message||String(e)}}async _controlApp(e){this._appBusy=!0,this._error=null;try{const t=await((e,t)=>we(e,{type:"ha_soc/terminal/app_control",action:t}))(this.hass,e);t.ok||(this._error=t.error||t.reason||"The app did not respond.")}catch(e){this._error=e.message||String(e)}finally{this._appBusy=!1,this._refresh()}}async _forgetPairing(){if(window.confirm("Forget the Terminal app's pairing? It will re-pair on its own the next time it starts.")){this._appBusy=!0;try{await(e=this.hass,we(e,{type:"ha_soc/terminal/forget_pairing"}))}catch(e){this._error=e.message||String(e)}finally{this._appBusy=!1,this._refresh()}var e}}async _closeOtherSession(e){this._sessionBusy=e;try{await Ve(this.hass,e)}catch(e){this._error=e.message||String(e)}finally{this._sessionBusy=null,this._refresh()}}async _runOnce(){const e=this._runCommand.trim();if(e&&!this._runBusy){this._runBusy=!0,this._runError=null,this._runOutput=null;try{const t=await((e,t,s)=>we(e,{type:"ha_soc/terminal/run",command:t,timeout_seconds:s}))(this.hass,e,this._runTimeout);this._runOutput=t,this._runHistory=[e,...this._runHistory.filter(t=>t!==e)].slice(0,10)}catch(e){this._runError=e.message||String(e)}finally{this._runBusy=!1}}}_renderStatusControls(){const e=this._status;return e?.installed?K`
      ${e.running?K`<button class="ha-btn" ?disabled=${this._appBusy} @click=${()=>this._controlApp("restart")}>
            Restart app
          </button>`:K`<button class="ha-btn" ?disabled=${this._appBusy} @click=${()=>this._controlApp("start")}>
            Start app
          </button>`}
      ${this._isOwner&&e.paired?K`<button class="ha-btn" ?disabled=${this._appBusy} @click=${()=>this._forgetPairing()}>
            Forget pairing
          </button>`:j}
    `:j}_renderSessionList(){const e=this._status?.sessions??[];if(!e.length)return j;const t=this.hass.user?.id,s=e.filter(e=>this._isOwner||e.user_id===t);return s.length?K`
      <div class="session-list">
        <h4 style="margin:8px 0 4px;">Open sessions</h4>
        <ul>
          ${s.map(e=>K`
              <li>
                <code>${e.session_id}</code> — ${e.user_id} — started ${new Date(e.started).toLocaleString()}
                (${e.bytes_in}B in / ${e.bytes_out}B out)
                <button
                  class="ha-btn"
                  ?disabled=${this._sessionBusy===e.session_id}
                  @click=${()=>this._closeOtherSession(e.session_id)}
                >
                  Close
                </button>
                <button class="ha-btn" @click=${()=>this._downloadTranscript(e.session_id)}>
                  Download transcript
                </button>
              </li>
            `)}
        </ul>
      </div>
    `:j}_renderExportButtons(){return this._open?K`
      <div class="export-row">
        <button class="ha-btn" @click=${()=>this._export("copy_screen",this._screenText(),"copy")}>
          Copy screen
        </button>
        <button class="ha-btn" @click=${()=>this._export("copy_all",this._allText(),"copy")}>
          Copy all
        </button>
        <button class="ha-btn" @click=${()=>this._export("copy_last",this._lastOutputText(),"copy")}>
          Copy last output
        </button>
        <button
          class="ha-btn"
          @click=${()=>this._export("download_screen",this._screenText(),"download",`ha-soc-terminal-${this._open?.session_id}`)}
        >
          Download screen
        </button>
        <button
          class="ha-btn"
          @click=${()=>this._export("download_all",this._allText(),"download",`ha-soc-terminal-${this._open?.session_id}`)}
        >
          Download all
        </button>
        <label class="font-ctl">
          <input
            type="checkbox"
            .checked=${this._stripAnsi}
            @change=${e=>this._stripAnsi=e.target.checked}
          />
          strip ANSI in transcript downloads
        </label>
        ${this._feedback?K`<span class="muted">${this._feedback}</span>`:j}
      </div>
    `:j}_renderRunCard(){const e=this._status,t=e?.targets.find(e=>"self"===e.id);return t?.available?K`
      <div class="card run-card">
        <h3 style="margin:0 0 6px;">Run a command</h3>
        <div class="run-row">
          <input
            type="text"
            .value=${this._runCommand}
            placeholder="e.g. ha core logs"
            @input=${e=>this._runCommand=e.target.value}
            @keydown=${e=>{"Enter"===e.key&&this._runOnce()}}
          />
          <select
            @change=${e=>this._runTimeout=Number(e.target.value)}
          >
            ${Kh.map(e=>K`<option value=${e} ?selected=${e===this._runTimeout}>${e}s</option>`)}
          </select>
          <button class="ha-btn" ?disabled=${this._runBusy} @click=${()=>this._runOnce()}>
            ${this._runBusy?"Running…":"Run"}
          </button>
        </div>
        ${this._runHistory.length?K`<div class="chips">
              ${this._runHistory.map(e=>K`<span class="chip" @click=${()=>this._runCommand=e}>${e}</span>`)}
            </div>`:j}
        ${this._runError?K`<div class="alert">${this._runError}</div>`:j}
        ${this._runOutput?K`
              <p class="muted" style="font-size:12px;margin:6px 0 2px;">
                exit ${this._runOutput.exit_code} — ${this._runOutput.duration_seconds}s${this._runOutput.truncated?" — output truncated at 256 KiB":""}
              </p>
              <pre class="rawlog">${this._runOutput.stdout||"(no output)"}</pre>
              <div class="export-row">
                <button
                  class="ha-btn"
                  @click=${()=>this._export("copy_run",this._runOutput.stdout,"copy")}
                >
                  Copy output
                </button>
                <button
                  class="ha-btn"
                  @click=${()=>this._export("download_run",this._runOutput.stdout,"download","ha-soc-terminal-run")}
                >
                  Download output
                </button>
              </div>
            `:j}
      </div>
    `:j}render(){const e=this._status,t=e?.targets.find(e=>"self"===e.id),s=!!t?.available&&!this._open&&!this._busy;return K`
      <div class="card term-shell">
        <div class="term-header">
          <h3 style="margin:0;">Terminal</h3>
          ${!1===e?.recording?K`<span class="muted">not recorded (app option)</span>`:K`<span class="recorded">● recorded</span>`}
          <span class="muted">
            ${e?e.supervisor?e.installed?e.running?e.paired?this._open?`Session ${this._open.session_id} on ${this._open.host}`:`Ready. ${e.sessions_open} of ${e.max_sessions} sessions open.`:"The Terminal app has not paired with HA SOC yet; it does so within a minute of starting.":"The Terminal app is installed but not running; start it under Settings, Apps.":"The HA SOC Terminal app is not installed.":"Needs a Supervisor-based install.":"Checking the Terminal app…"}
          </span>
          <span class="spacer"></span>
          ${this._renderStatusControls()}
          ${this._renderFontControls()}
          ${this._open?K`<button class="ha-btn" @click=${()=>this._close("user_closed")}>Close session</button>`:K`<button class="ha-btn" ?disabled=${!s} @click=${()=>this._start()}>
                ${this._busy?"Opening…":"Open session"}
              </button>`}
          <button class="ha-btn" ?disabled=${this._busy} @click=${()=>this._refresh()}>Refresh</button>
        </div>
        ${this._error?K`<div class="alert">${this._error}</div>`:j}
        <div class="term-box" @click=${()=>this._term?.focus()}></div>
        ${this._renderExportButtons()}
        ${this._ended?K`<p class="muted ended">
              ${jh[this._ended.reason]??this._ended.reason}
              ${this._ended.duration?` Duration ${Math.round(this._ended.duration/60)} min.`:""}
              The session's open and close records are in the Audit Log.
            </p>`:j}
        <p class="muted" style="font-size:11.5px;margin:0;">
          Executes only on this server, in the Terminal app's own container. Paste with
          Ctrl+Shift+V or the browser's paste; scroll with the mouse wheel. Every session is
          recorded by the app unless its option is off, and opens and closes are audited here.
          Font, size and line spacing are remembered in this browser; a family listed as not
          installed is missing on this machine, not on the server.
        </p>
        ${this._renderSessionList()}
        ${this._renderRunCard()}
      </div>
    `}};tc.styles=[qe,o('/**\n * Copyright (c) 2014 The xterm.js authors. All rights reserved.\n * Copyright (c) 2012-2013, Christopher Jeffrey (MIT License)\n * https://github.com/chjj/term.js\n * @license MIT\n *\n * Permission is hereby granted, free of charge, to any person obtaining a copy\n * of this software and associated documentation files (the "Software"), to deal\n * in the Software without restriction, including without limitation the rights\n * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n * copies of the Software, and to permit persons to whom the Software is\n * furnished to do so, subject to the following conditions:\n *\n * The above copyright notice and this permission notice shall be included in\n * all copies or substantial portions of the Software.\n *\n * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n * THE SOFTWARE.\n *\n * Originally forked from (with the author\'s permission):\n *   Fabrice Bellard\'s javascript vt100 for jslinux:\n *   http://bellard.org/jslinux/\n *   Copyright (c) 2011 Fabrice Bellard\n *   The original design remains. The terminal itself\n *   has been extended to include xterm CSI codes, among\n *   other features.\n */\n\n/**\n *  Default styles for xterm.js\n */\n\n.xterm {\n    cursor: text;\n    position: relative;\n    user-select: none;\n    -ms-user-select: none;\n    -webkit-user-select: none;\n}\n\n.xterm.focus,\n.xterm:focus {\n    outline: none;\n}\n\n.xterm .xterm-helpers {\n    position: absolute;\n    top: 0;\n    /**\n     * The z-index of the helpers must be higher than the canvases in order for\n     * IMEs to appear on top.\n     */\n    z-index: 5;\n}\n\n.xterm .xterm-helper-textarea {\n    padding: 0;\n    border: 0;\n    margin: 0;\n    /* Move textarea out of the screen to the far left, so that the cursor is not visible */\n    position: absolute;\n    opacity: 0;\n    left: -9999em;\n    top: 0;\n    width: 0;\n    height: 0;\n    z-index: -5;\n    /** Prevent wrapping so the IME appears against the textarea at the correct position */\n    white-space: nowrap;\n    overflow: hidden;\n    resize: none;\n}\n\n.xterm .composition-view {\n    /* TODO: Composition position got messed up somewhere */\n    background: #000;\n    color: #FFF;\n    display: none;\n    position: absolute;\n    white-space: nowrap;\n    z-index: 1;\n}\n\n.xterm .composition-view.active {\n    display: block;\n}\n\n.xterm .xterm-viewport {\n    /* On OS X this is required in order for the scroll bar to appear fully opaque */\n    background-color: #000;\n    overflow-y: scroll;\n    cursor: default;\n    position: absolute;\n    right: 0;\n    left: 0;\n    top: 0;\n    bottom: 0;\n}\n\n.xterm .xterm-screen {\n    position: relative;\n}\n\n.xterm .xterm-screen canvas {\n    position: absolute;\n    left: 0;\n    top: 0;\n}\n\n.xterm-char-measure-element {\n    display: inline-block;\n    visibility: hidden;\n    position: absolute;\n    top: 0;\n    left: -9999em;\n    line-height: normal;\n}\n\n.xterm.enable-mouse-events {\n    /* When mouse events are enabled (eg. tmux), revert to the standard pointer cursor */\n    cursor: default;\n}\n\n.xterm.xterm-cursor-pointer,\n.xterm .xterm-cursor-pointer {\n    cursor: pointer;\n}\n\n.xterm.column-select.focus {\n    /* Column selection mode */\n    cursor: crosshair;\n}\n\n.xterm .xterm-accessibility:not(.debug),\n.xterm .xterm-message {\n    position: absolute;\n    left: 0;\n    top: 0;\n    bottom: 0;\n    right: 0;\n    z-index: 10;\n    color: transparent;\n    pointer-events: none;\n}\n\n.xterm .xterm-accessibility-tree:not(.debug) *::selection {\n  color: transparent;\n}\n\n.xterm .xterm-accessibility-tree {\n  font-family: monospace;\n  user-select: text;\n  white-space: pre;\n}\n\n.xterm .xterm-accessibility-tree > div {\n  transform-origin: left;\n  width: fit-content;\n}\n\n.xterm .live-region {\n    position: absolute;\n    left: -9999px;\n    width: 1px;\n    height: 1px;\n    overflow: hidden;\n}\n\n.xterm-dim {\n    /* Dim should not apply to background, so the opacity of the foreground color is applied\n     * explicitly in the generated class and reset to 1 here */\n    opacity: 1 !important;\n}\n\n.xterm-underline-1 { text-decoration: underline; }\n.xterm-underline-2 { text-decoration: double underline; }\n.xterm-underline-3 { text-decoration: wavy underline; }\n.xterm-underline-4 { text-decoration: dotted underline; }\n.xterm-underline-5 { text-decoration: dashed underline; }\n\n.xterm-overline {\n    text-decoration: overline;\n}\n\n.xterm-overline.xterm-underline-1 { text-decoration: overline underline; }\n.xterm-overline.xterm-underline-2 { text-decoration: overline double underline; }\n.xterm-overline.xterm-underline-3 { text-decoration: overline wavy underline; }\n.xterm-overline.xterm-underline-4 { text-decoration: overline dotted underline; }\n.xterm-overline.xterm-underline-5 { text-decoration: overline dashed underline; }\n\n.xterm-strikethrough {\n    text-decoration: line-through;\n}\n\n.xterm-screen .xterm-decoration-container .xterm-decoration {\n\tz-index: 6;\n\tposition: absolute;\n}\n\n.xterm-screen .xterm-decoration-container .xterm-decoration.xterm-decoration-top-layer {\n\tz-index: 7;\n}\n\n.xterm-decoration-overview-ruler {\n    z-index: 8;\n    position: absolute;\n    top: 0;\n    right: 0;\n    pointer-events: none;\n}\n\n.xterm-decoration-top {\n    z-index: 2;\n    position: relative;\n}\n\n\n\n/* Derived from vs/base/browser/ui/scrollbar/media/scrollbar.css */\n\n/* xterm.js customization: Override xterm\'s cursor style */\n.xterm .xterm-scrollable-element > .scrollbar {\n    cursor: default;\n}\n\n/* Arrows */\n.xterm .xterm-scrollable-element > .scrollbar > .scra {\n\tcursor: pointer;\n\tfont-size: 11px !important;\n}\n\n.xterm .xterm-scrollable-element > .visible {\n\topacity: 1;\n\n\t/* Background rule added for IE9 - to allow clicks on dom node */\n\tbackground:rgba(0,0,0,0);\n\n\ttransition: opacity 100ms linear;\n\t/* In front of peek view */\n\tz-index: 11;\n}\n.xterm .xterm-scrollable-element > .invisible {\n\topacity: 0;\n\tpointer-events: none;\n}\n.xterm .xterm-scrollable-element > .invisible.fade {\n\ttransition: opacity 800ms linear;\n}\n\n/* Scrollable Content Inset Shadow */\n.xterm .xterm-scrollable-element > .shadow {\n\tposition: absolute;\n\tdisplay: none;\n}\n.xterm .xterm-scrollable-element > .shadow.top {\n\tdisplay: block;\n\ttop: 0;\n\tleft: 3px;\n\theight: 3px;\n\twidth: 100%;\n\tbox-shadow: var(--vscode-scrollbar-shadow, #000) 0 6px 6px -6px inset;\n}\n.xterm .xterm-scrollable-element > .shadow.left {\n\tdisplay: block;\n\ttop: 3px;\n\tleft: 0;\n\theight: 100%;\n\twidth: 3px;\n\tbox-shadow: var(--vscode-scrollbar-shadow, #000) 6px 0 6px -6px inset;\n}\n.xterm .xterm-scrollable-element > .shadow.top-left-corner {\n\tdisplay: block;\n\ttop: 0;\n\tleft: 0;\n\theight: 3px;\n\twidth: 3px;\n}\n.xterm .xterm-scrollable-element > .shadow.top.left {\n\tbox-shadow: var(--vscode-scrollbar-shadow, #000) 6px 0 6px -6px inset;\n}\n'),a`
      .term-shell {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .term-header {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        font-size: 12.5px;
      }
      .term-header .spacer {
        flex: 1;
      }
      .term-box {
        background: var(--soc-term-bg, #1c2128);
        border-radius: 8px;
        padding: 8px;
        min-height: 420px;
        height: calc(100vh - 280px);
        overflow: hidden;
      }
      .term-box .xterm {
        height: 100%;
      }
      .font-ctl {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: var(--secondary-text-color);
      }
      .font-ctl select {
        font: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        padding: 2px 4px;
      }
      .recorded {
        color: var(--error-color, #db4437);
        font-weight: 600;
      }
      .ended {
        margin-top: 6px;
      }
      .export-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        font-size: 12px;
      }
      .session-list ul {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12.5px;
      }
      .run-card {
        margin-top: 4px;
      }
      .run-row {
        display: flex;
        gap: 8px;
      }
      .run-row input[type="text"] {
        flex: 1;
        font: inherit;
        padding: 4px 8px;
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
      }
      .chips {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-top: 6px;
      }
      .chip {
        cursor: pointer;
        font-size: 11.5px;
        padding: 2px 8px;
        border-radius: 100px;
        background: var(--secondary-background-color, #eee);
        color: var(--secondary-text-color);
      }
      .rawlog {
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 300px;
        overflow: auto;
      }
    `],e([ue({attribute:!1})],tc.prototype,"hass",void 0),e([pe()],tc.prototype,"_status",void 0),e([pe()],tc.prototype,"_error",void 0),e([pe()],tc.prototype,"_open",void 0),e([pe()],tc.prototype,"_ended",void 0),e([pe()],tc.prototype,"_prefs",void 0),e([pe()],tc.prototype,"_busy",void 0),e([pe()],tc.prototype,"_isOwner",void 0),e([pe()],tc.prototype,"_feedback",void 0),e([pe()],tc.prototype,"_appBusy",void 0),e([pe()],tc.prototype,"_runCommand",void 0),e([pe()],tc.prototype,"_runTimeout",void 0),e([pe()],tc.prototype,"_runBusy",void 0),e([pe()],tc.prototype,"_runOutput",void 0),e([pe()],tc.prototype,"_runError",void 0),e([pe()],tc.prototype,"_runHistory",void 0),e([pe()],tc.prototype,"_stripAnsi",void 0),e([pe()],tc.prototype,"_sessionBusy",void 0),e([
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function(e){return(t,s,i)=>((e,t,s)=>(s.configurable=!0,s.enumerable=!0,Reflect.decorate&&"object"!=typeof t&&Object.defineProperty(e,t,s),s))(t,s,{get(){return(t=>t.renderRoot?.querySelector(e)??null)(this)}})}(".term-box")],tc.prototype,"_box",void 0),tc=e([he("ha-soc-terminal-view")],tc);let sc=class extends ae{constructor(){super(...arguments),this.narrow=!1,this._tab="dashboard",this._access=null,this._version=null,this._probe=null,this._customizeMode=!1,this._pendingNetworkFilter=null}connectedCallback(){super.connectedCallback(),this._loadAccess(),this._loadFooterInfo()}async _loadAccess(){try{this._access=await Me(this.hass)}catch{this._access={is_owner:!1,access_level:"owner_only",allowed:!1}}}async _loadFooterInfo(){try{this._version=(await(e=this.hass,we(e,{type:"ha_soc/version/get"}))).version}catch{this._version=null}var e;try{this._probe=await Be(this.hass)}catch{this._probe=null}}_bundleIsStale(){const e=this.panel?.config?.bundle_token,t=function(){try{return new URL(import.meta.url).searchParams.get("v")}catch{return null}}();return"string"==typeof e&&e.length>0&&null!==t&&e!==t}_renderStaleBanner(){return this._bundleIsStale()?K`
      <div class="stale-banner" role="status">
        <span>
          HA SOC was updated on the server. This page is still running the previous version; reload to use the
          new one.
        </span>
        <button type="button" @click=${()=>window.location.reload()}>Reload</button>
      </div>
    `:K``}_renderFooter(){if(!this._version)return K``;const e=this._probe?.installed&&this._probe.version?` · HA SOC Probe v${this._probe.version}`:"";return K`<div class="footer">HA SOC v${this._version}${e}</div>`}render(){if(null===this._access)return K`<div class="header">🛡️ HA SOC</div>`;if(!this._access.allowed)return K`
        <div class="denied">
          <div class="icon">🛡️🚫</div>
          <h2>Access restricted</h2>
          <p>
            HA SOC is currently set to <strong>account owner only</strong>. Your account
            is an administrator, but not the account owner, so this panel and its data
            aren't reachable from here.
          </p>
          <p>
            The owner can open this up to every administrator from
            <strong>Settings → Devices &amp; Services → HA SOC → Configure</strong>, or
            from this panel's own Settings tab once they've signed in.
          </p>
        </div>
        ${this._renderFooter()}
      `;const e=(t=this._tab,_e.find(e=>e.tabs.some(e=>e.id===t))??_e[0]);var t;return K`
      ${this._renderStaleBanner()}
      <div class="header">
        <div class="brand">
          <span class="brand-mark">SOC</span>
          <span>
            <span class="brand-title">HA SOC Security Console</span>
            <span class="brand-context">Protected detail workspace</span>
          </span>
        </div>
        <span
          class="access-indicator"
          title=${this._access.is_owner?"Owner access":"Administrator access"}
          aria-label=${this._access.is_owner?"Owner access":"Administrator access"}
        >
          <span class="access-indicator-label"
            >${this._access.is_owner?"Owner access":"Administrator access"}</span
          >
        </span>
        ${"settings"===this._tab?K``:K`
              <button
                type="button"
                class="customize-btn ${this._customizeMode?"active":""}"
                @click=${()=>this._customizeMode=!this._customizeMode}
              >
                ${this._customizeMode?"Done":"Customize"}
              </button>
            `}
      </div>
      <nav class="tabs" aria-label="HA SOC workspaces">
        ${_e.map(t=>!!t.ownerOnly&&!this._access?.is_owner?K`
              <button type="button" class="tab disabled" title="Only available to the account owner" disabled>
                ${t.label}<span class="lock">🔒</span>
              </button>
            `:K`
            <button
              type="button"
              class="tab ${e.id===t.id?"active":""}"
              aria-current=${e.id===t.id?"page":"false"}
              @click=${()=>this._selectTab(t.defaultTab)}
            >
              ${t.label}
            </button>
          `)}
      </nav>
      ${e.tabs.length>1?K`
            <nav class="subtabs" aria-label="${e.label} views">
              ${e.tabs.map(e=>K`
                  <button
                    type="button"
                    class="subtab ${this._tab===e.id?"active":""}"
                    aria-current=${this._tab===e.id?"page":"false"}
                    @click=${()=>this._selectTab(e.id)}
                  >
                    ${e.label}
                  </button>
                `)}
            </nav>
          `:K``}
      <div @ha-soc-navigate=${this._onNavigate}>${this._renderTab()}</div>
      ${this._renderFooter()}
    `}_selectTab(e){this._tab=e,this._customizeMode=!1}_onNavigate(e){this._tab=e.detail.tab,this._customizeMode=!1,e.detail.clientFilter&&(this._pendingNetworkFilter=e.detail.clientFilter)}_renderTab(){const e=this._customizeMode;switch(this._tab){case"users":return K`<ha-soc-users-view .hass=${this.hass} .customizeMode=${e}></ha-soc-users-view>`;case"audit":return K`<ha-soc-audit-view .hass=${this.hass} .customizeMode=${e}></ha-soc-audit-view>`;case"permissions":return K`<ha-soc-permissions-view .hass=${this.hass} .customizeMode=${e}></ha-soc-permissions-view>`;case"scanner":return K`<ha-soc-scanner-view .hass=${this.hass} .customizeMode=${e}></ha-soc-scanner-view>`;case"logs":return K`<ha-soc-logs-view .hass=${this.hass} .customizeMode=${e}></ha-soc-logs-view>`;case"peripherals":return K`<ha-soc-peripherals-view .hass=${this.hass} .customizeMode=${e}></ha-soc-peripherals-view>`;case"network":return K`<ha-soc-network-view
          .hass=${this.hass}
          .customizeMode=${e}
          .initialClientFilter=${this._pendingNetworkFilter}
          @client-filter-consumed=${()=>this._pendingNetworkFilter=null}
        ></ha-soc-network-view>`;case"network_security":return K`<ha-soc-network-security-view
          .hass=${this.hass}
          .customizeMode=${e}
        ></ha-soc-network-security-view>`;case"entity_remap":return K`<ha-soc-entity-remap-view .hass=${this.hass} .customizeMode=${e}></ha-soc-entity-remap-view>`;case"entity_map":return K`<ha-soc-entity-map-view .hass=${this.hass}></ha-soc-entity-map-view>`;case"dashboard_files":return K`<ha-soc-dashboard-files-view .hass=${this.hass}></ha-soc-dashboard-files-view>`;case"integration_security":return K`<ha-soc-integration-security-view
          .hass=${this.hass}
          .customizeMode=${e}
        ></ha-soc-integration-security-view>`;case"terminal":return K`<ha-soc-terminal-view .hass=${this.hass}></ha-soc-terminal-view>`;case"settings":return this._access?.is_owner?K`<ha-soc-settings-view .hass=${this.hass}></ha-soc-settings-view>`:K`<div class="denied"><div class="icon">🔒</div><h2>Owner only</h2>
            <p>The Settings tab is available to the account owner only.</p></div>`;default:return K`<ha-soc-dashboard-view .hass=${this.hass} .customizeMode=${e}></ha-soc-dashboard-view>`}}};sc.styles=a`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100vh;
      container-type: inline-size;
    }
    .tabs {
      display: flex;
      gap: 6px;
      border-top: 1px solid var(--divider-color);
      border-bottom: 1px solid var(--divider-color);
      padding: 9px max(16px, calc((100% - 1400px) / 2));
      background: var(--card-background-color, #fff);
      overflow-x: auto;
      position: sticky;
      top: 0;
      z-index: 5;
      scrollbar-width: thin;
    }
    .subtabs {
      display: flex;
      gap: 4px;
      padding: 7px max(16px, calc((100% - 1400px) / 2));
      overflow-x: auto;
      background: var(--primary-background-color);
      border-bottom: 1px solid var(--divider-color);
      scrollbar-width: thin;
    }
    .tab {
      appearance: none;
      font: inherit;
      background: transparent;
      border: 1px solid transparent;
      border-radius: 9px;
      padding: 8px 11px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 550;
      color: var(--secondary-text-color);
      white-space: nowrap;
    }
    .tab:hover,
    .tab:focus-visible {
      color: var(--primary-text-color);
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.045);
      outline: none;
    }
    .tab.active {
      color: var(--primary-color);
      border-color: rgba(var(--rgb-primary-color, 3, 155, 229), 0.24);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.1);
    }
    .tab.disabled {
      color: var(--disabled-text-color, #b0b0b0);
      cursor: not-allowed;
    }
    .tab.disabled .lock {
      font-size: 11px;
      margin-left: 4px;
      opacity: 0.8;
    }
    .subtab {
      appearance: none;
      border: 0;
      border-radius: 7px;
      padding: 7px 10px;
      background: transparent;
      color: var(--secondary-text-color);
      cursor: pointer;
      font: inherit;
      font-size: 12.5px;
      white-space: nowrap;
    }
    .subtab:hover,
    .subtab:focus-visible {
      color: var(--primary-text-color);
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.045);
    }
    .subtab.active {
      color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.09);
      font-weight: 600;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 17px max(16px, calc((100% - 1400px) / 2)) 14px;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
    }
    .brand-mark {
      width: 34px;
      height: 34px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      background: var(--primary-color);
      color: #fff;
      font-size: 12px;
      font-weight: 750;
      letter-spacing: 0.04em;
    }
    .brand-title {
      display: block;
      font-size: 18px;
      font-weight: 680;
      line-height: 1.15;
    }
    .brand-context {
      display: block;
      margin-top: 2px;
      color: var(--secondary-text-color);
      font-size: 11.5px;
    }
    .access-indicator {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--success-color, #0f9d58);
      font-size: 12px;
      white-space: nowrap;
    }
    .access-indicator::before {
      content: "";
      width: 8px;
      height: 10px;
      border: 1.5px solid currentColor;
      border-radius: 5px 5px 4px 4px;
      clip-path: polygon(50% 0, 100% 18%, 90% 72%, 50% 100%, 10% 72%, 0 18%);
    }
    .customize-btn {
      font-size: 13px;
      font-weight: 500;
      padding: 7px 14px;
      border-radius: 100px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      cursor: pointer;
    }
    .customize-btn.active {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: #fff;
    }
    .denied {
      max-width: 480px;
      margin: 15vh auto 0;
      padding: 32px;
      text-align: center;
      color: var(--primary-text-color);
    }
    .denied .icon {
      font-size: 40px;
    }
    .denied h2 {
      margin: 12px 0 4px;
      font-size: 18px;
    }
    .denied p {
      color: var(--secondary-text-color);
      font-size: 13.5px;
      line-height: 1.5;
    }
    .stale-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 12px max(16px, calc((100% - 1400px) / 2)) 0;
      padding: 10px 14px;
      border: 1px solid rgba(var(--rgb-primary-color, 3, 155, 229), 0.35);
      border-radius: var(--ha-card-border-radius, 12px);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.08);
      color: var(--primary-text-color);
      font-size: 13px;
    }
    .stale-banner span {
      flex: 1;
    }
    .stale-banner button {
      font: inherit;
      font-size: 13px;
      font-weight: 600;
      padding: 6px 14px;
      border-radius: 100px;
      border: 1px solid var(--primary-color);
      background: var(--primary-color);
      color: #fff;
      cursor: pointer;
    }
    .footer {
      padding: 10px 16px 14px;
      font-size: 11px;
      color: var(--secondary-text-color);
      text-align: center;
    }
    :host([narrow]) .header {
      padding-top: 12px;
    }
    :host([narrow]) .access-indicator .access-indicator-label {
      display: none;
    }
    :host([narrow]) .brand-title {
      font-size: 15px;
    }
    :host([narrow]) .brand-context {
      font-size: 11px;
    }
    :host([narrow]) .customize-btn {
      padding: 7px 10px;
    }
    @container (max-width: 420px) {
      .header {
        padding-top: 12px;
      }
      .customize-btn {
        padding: 7px 10px;
      }
    }
  `,e([ue({attribute:!1})],sc.prototype,"hass",void 0),e([ue({type:Boolean,reflect:!0})],sc.prototype,"narrow",void 0),e([ue({attribute:!1})],sc.prototype,"panel",void 0),e([pe()],sc.prototype,"_tab",void 0),e([pe()],sc.prototype,"_access",void 0),e([pe()],sc.prototype,"_version",void 0),e([pe()],sc.prototype,"_probe",void 0),e([pe()],sc.prototype,"_customizeMode",void 0),e([pe()],sc.prototype,"_pendingNetworkFilter",void 0),sc=e([he("ha-soc-panel")],sc);export{sc as HaSocPanel};
