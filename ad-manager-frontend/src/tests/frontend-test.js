const { Builder, By, Key, until } = require('selenium-webdriver');

const { expect } = require('chai');

describe('NavBar Tests', function() {
    let driver;

    before(async function() {
        driver = await new Builder().forBrowser('chrome').build();
    });

    it('should navigate to Inventory page when Inventory link is clicked', async function() {
        this.timeout(10000); 
    
        await driver.get('http://localhost:3001');
        const inventoryLink = await driver.findElement(By.linkText('Inventory'));
        await inventoryLink.click();

        const table = await driver.findElement(By.tagName('table'));
    
        const tableRows = await table.findElements(By.tagName('tr'));
        
        const columnHeaderCells = await tableRows[0].findElements(By.tagName('th'));
    
        expect(columnHeaderCells.length).to.be.at.least(3);
    
        expect(await columnHeaderCells[0].getText()).to.equal('Publisher ID');
    
        expect(await columnHeaderCells[1].getText()).to.equal('Publisher Name');
    
        expect(await columnHeaderCells[2].getText()).to.equal('State');
        
        await driver.wait(until.elementLocated(By.xpath("//button[contains(text(),'Add new publisher')]")));
        
        const addButton = await driver.findElement(By.xpath("//button[contains(text(),'Add new publisher')]"));
        expect(await addButton.isDisplayed()).to.equal(true);
    });
    

    it('should navigate to Demand page when Demand link is clicked', async function() {
        await driver.get('http://localhost:3001');
        const demandLink = await driver.findElement(By.linkText('Demand'));
        await demandLink.click();
        
        const table = await driver.findElement(By.tagName('table'));
    
        const tableRows = await table.findElements(By.tagName('tr'));
        
        const columnHeaderCells = await tableRows[0].findElements(By.tagName('th'));
    
        expect(columnHeaderCells.length).to.be.at.least(3);
    
        expect(await columnHeaderCells[0].getText()).to.equal('Advertiser ID');
    
        expect(await columnHeaderCells[1].getText()).to.equal('Advertiser Name');
    
        expect(await columnHeaderCells[2].getText()).to.equal('State');
    
    
        const addAdvertiserButton = await driver.findElement(By.xpath("//button[contains(text(), 'Add new Advertiser')]"));
        expect(addAdvertiserButton).to.exist;
    });
    
    it('should navigate to Reports page when Reports link is clicked', async function() {
        await driver.get('http://localhost:3001');
        const reportsLink = await driver.findElement(By.linkText('Reports'));
        await reportsLink.click();
    
        const table = await driver.findElement(By.tagName('table'));
    
        const tableRows = await table.findElements(By.tagName('tr'));
        
        const columnHeaderCells = await tableRows[0].findElements(By.tagName('th'));
    
        expect(columnHeaderCells.length).to.be.at.least(3);
    
        expect(await columnHeaderCells[0].getText()).to.equal('Ad ID');
    
        expect(await columnHeaderCells[1].getText()).to.equal('Clicks');
    
        expect(await columnHeaderCells[2].getText()).to.equal('Renders');

        const refreshButton = await driver.findElement(By.xpath("//button[contains(text(), 'Refresh')]"));
        expect(refreshButton).to.exist;
    });
    

    it('should display correct content on homepage', async function() {
        await driver.get('http://localhost:3001');
        const homepageContent = await driver.findElement(By.tagName('h1')).getText();
        expect(homepageContent).to.equal('Welcome to Ad Pulse');
    });

    after(async function() {
        await driver.quit();
    });
});
