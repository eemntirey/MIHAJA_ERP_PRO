// src/pages/Catalogue.jsx
import React from 'react';
import Catalog from '../components/landing/Catalog';
import Seo from '../components/Seo';
import PublicHeader from '../components/PublicHeader';

const CATALOGUE_SEO_DATA = {
  '@context': 'https://schema.org',
  '@type': 'CollectionPage',
  name: 'Catalogue produits | MIHAJA ERP PRO',
  url: 'https://erp.sekoliko.com/catalogue',
  description: 'Découvrez les produits disponibles sur la vitrine publique MIHAJA ERP PRO.',
  isPartOf: {
    '@type': 'WebSite',
    name: 'MIHAJA ERP PRO',
    url: 'https://erp.sekoliko.com/',
  },
};

const Catalogue = () => {
  return (
    <>
      <Seo
        title="Catalogue produits | MIHAJA ERP PRO"
        description="Découvrez les produits disponibles sur la vitrine publique MIHAJA ERP PRO."
        canonical="https://erp.sekoliko.com/catalogue"
        structuredData={CATALOGUE_SEO_DATA}
      />
      <div className="landing-root">
        <PublicHeader />
        <Catalog />
      </div>
    </>
  );
};

export default Catalogue;
