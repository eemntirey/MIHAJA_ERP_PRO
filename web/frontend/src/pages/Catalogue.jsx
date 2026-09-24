// src/pages/Catalogue.jsx
import React from 'react';
import Seo from '../components/Seo';
import Catalog from '../components/landing/Catalog';

const Catalogue = () => {
  return (
    <>
      <Seo
        title="Catalogue produits | MIHAJA ERP PRO"
        description="Découvrez le catalogue public de produits proposé par les entreprises présentes sur MIHAJA ERP PRO."
        canonical="https://erp.sekoliko.com/catalogue"
      />
    <div className="landing-root">
      <Catalog />
    </div>
    </>
  );
};

export default Catalogue;
