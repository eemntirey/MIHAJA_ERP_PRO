import { useEffect } from 'react';

const SITE_URL = 'https://erp.sekoliko.com';
const DEFAULT_TITLE = 'MIHAJA ERP PRO | ERP SaaS pour les entreprises à Madagascar';
const DEFAULT_DESCRIPTION =
  'MIHAJA ERP PRO est un ERP SaaS pour gérer stocks, ventes, achats, factures, clients et livraisons pour les entreprises à Madagascar.';

const upsertMeta = (attribute, key, content) => {
  let element = document.head.querySelector(`meta[${attribute}="${key}"]`);
  if (!element) {
    element = document.createElement('meta');
    element.setAttribute(attribute, key);
    document.head.appendChild(element);
  }
  element.setAttribute('content', content);
  return element;
};

const upsertLink = (rel, href) => {
  let element = document.head.querySelector(`link[rel="${rel}"]`);
  if (!element) {
    element = document.createElement('link');
    element.setAttribute('rel', rel);
    document.head.appendChild(element);
  }
  element.setAttribute('href', href);
  return element;
};

const upsertJsonLd = (id, data) => {
  let element = document.head.querySelector(`script[data-seo-jsonld="${id}"]`);
  if (!data) {
    element?.remove();
    return null;
  }
  if (!element) {
    element = document.createElement('script');
    element.type = 'application/ld+json';
    element.dataset.seoJsonld = id;
    document.head.appendChild(element);
  }
  element.textContent = JSON.stringify(data);
  return element;
};

export const Seo = ({
  title = DEFAULT_TITLE,
  description = DEFAULT_DESCRIPTION,
  canonical,
  noindex = false,
  type = 'website',
  image,
  structuredData,
}) => {
  useEffect(() => {
    const canonicalUrl = canonical || `${SITE_URL}${window.location.pathname}`;
    const previousTitle = document.title;

    document.title = title;
    upsertMeta('name', 'description', description);
    upsertMeta('name', 'robots', noindex ? 'noindex,nofollow,noarchive' : 'index,follow');
    upsertMeta('property', 'og:title', title);
    upsertMeta('property', 'og:description', description);
    upsertMeta('property', 'og:type', type);
    upsertMeta('property', 'og:url', canonicalUrl);
    upsertMeta('property', 'og:site_name', 'MIHAJA ERP PRO');
    upsertMeta('name', 'twitter:card', image ? 'summary_large_image' : 'summary');
    upsertMeta('name', 'twitter:title', title);
    upsertMeta('name', 'twitter:description', description);

    if (image) {
      upsertMeta('property', 'og:image', image);
      upsertMeta('name', 'twitter:image', image);
    }

    upsertLink('canonical', canonicalUrl);
    upsertJsonLd('page', structuredData);

    return () => {
      document.title = previousTitle || DEFAULT_TITLE;
      const jsonLd = document.head.querySelector('script[data-seo-jsonld="page"]');
      jsonLd?.remove();
    };
  }, [title, description, canonical, noindex, type, image, structuredData]);

  return null;
};

export default Seo;
